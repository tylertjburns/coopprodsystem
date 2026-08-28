import time
import threading
import uuid

from typing import List, Optional, Callable, Dict, Tuple
from cooptools.timeTracker.decay import TimedDecay
import logging
import coopprodsystem.events as evnts
from coopprodsystem.factory.stationResourceDefinition import StationResourceDefinition
from coopprodsystem.factory.stationStatus import StationStatus
from cooptools.coopEnum import CoopEnum
from enum import auto
from cooptools.expertise.expertiseSchedules import ExpertiseSchedule, ExpertiseCalculator
from cooptools.expertise.expertiseArgs import ExpertiseArgs
from cooptools.coopthreading import AsyncWorker
from cooptools.timeWindow import TaggedTimeWindow, TimeWindow
from cooptools.ideas.metrics import Metrics
from cooptools.qualifiers import WhiteBlackListQualifier
import coopstorage.storage.loc_load.dcs as dcs
from coopstorage.storage.loc_load.storage import Storage
from coopstorage.storage.loc_load.location import Location

logger = logging.getLogger(__name__)

ProductionTimeSecCallback = Callable[[], float]
ResourceUomKey = Tuple[dcs.Resource, dcs.UnitOfMeasure]

# Key under which a state block carries its own version. Spelled out rather than
# imported: Station satisfies a consuming framework's persistence protocol
# structurally, by having to_state/apply_state, and must not take a dependency on
# whichever framework happens to be persisting it.
STATE_VERSION_KEY = 'v'


def _contents_to_state(by_resource_uom: Dict[ResourceUomKey, float]) -> List[dict]:
    """Store contents as resource/uom *names*.

    Never as the Resource objects themselves, and never reconstructed from these
    names on the way back: Resource and UnitOfMeasure are identity-typed -- they
    hash by a generated id rather than by their fields -- so a rebuilt
    `Resource(name='FOOD')` is a different resource from the one this station's
    containers are qualified to hold, and every add against it would be refused.
    See _resolve_key for how the name is turned back into the right instance.
    """
    return sorted(
        ({'resource': resource.name, 'uom': uom.name, 'qty': qty}
         for (resource, uom), qty in by_resource_uom.items() if qty > 0),
        key=lambda entry: (entry['resource'], entry['uom']),
    )


def _resolve_key(loc_ids: Dict[ResourceUomKey, str], resource_name: str,
                 uom_name: str) -> Optional[ResourceUomKey]:
    """The station's own (Resource, UoM) key matching these names, or None.

    The station's definitions are the lookup table: it can only ever hold what its
    recipe declares, so a saved content naming something absent from the recipe is
    something the recipe no longer has a slot for, and dropping it is correct.
    """
    for key in loc_ids:
        if key[0].name == resource_name and key[1].name == uom_name:
            return key
    return None


class AtMaxCapacityException(Exception):
    def __init__(self):
        super().__init__(str(type(self)))


class OutputStorageToFullToProduceException(Exception):
    def __init__(self):
        super().__init__(str(type(self)))


class NotEnoughInputToProduceException(Exception):
    def __init__(self):
        super().__init__(str(type(self)))


class InvalidInputToAddToStationException(Exception):
    def __init__(self):
        super().__init__(str(type(self)))


class StationProductionStrategy(CoopEnum):
    PRODUCE_IF_ALL_SPACE_AVAIL = auto()
    PRODUCE_IF_ANY_SPACE_AVAIL = auto()


def _build_slot_storage(id_prefix: str, defs: List[StationResourceDefinition]) -> Tuple[Storage, Dict[ResourceUomKey, str]]:
    """One Location per resource-def, each pre-populated with a single Container
    scoped (via uom_capacities + resource_qualifier) to that def's resource/uom.
    Bypasses the TransferRequest/reservation pipeline -- a Station's own input/output
    storage has no other actor contending for it."""
    locs = []
    containers = []
    loc_ids: Dict[ResourceUomKey, str] = {}
    for ii, defin in enumerate(defs):
        loc_id = f"{id_prefix}_{ii}"
        container = dcs.Container(
            uom=defin.content.uom,
            uom_capacities=frozenset([dcs.UoMCapacity(uom=defin.content.uom, capacity=defin.storage_capacity)]),
            resource_qualifier=WhiteBlackListQualifier(white_list=[defin.content.resource]),
        )
        loc = Location(
            id=loc_id,
            location_meta=dcs.LocationMeta(dims=(1, 1, 1), capacity=1),
            coords=(0, 0, 0),
        )
        loc.store_containers([container.id])
        locs.append(loc)
        containers.append(container)
        loc_ids[(defin.content.resource, defin.content.uom)] = loc_id
    return Storage(locs=locs, containers=containers, id=id_prefix), loc_ids


class Station:
    def __init__(self,
                 output: List[StationResourceDefinition],
                 production_timer_sec_callback: ProductionTimeSecCallback,
                 input_reqs: List[StationResourceDefinition] = None,
                 id: str = None,
                 type: str = None,
                 production_strategy: StationProductionStrategy = None,
                 expertise_schedule: ExpertiseSchedule = None,
                 start_on_init: bool = False,
                 ):
        self.id = id if id else uuid.uuid4()
        self.type = type
        self._input_reqs = input_reqs or []
        self._output = output
        self._input_storage, self._input_loc_ids = _build_slot_storage(f"{self.id}_input", self._input_reqs)
        self._output_storage, self._output_loc_ids = _build_slot_storage(f"{self.id}_output", output)
        self._production_time_sec_callback = production_timer_sec_callback
        self._production_timer: Optional[TimedDecay] = None
        self.production_strategy: StationProductionStrategy = production_strategy or StationProductionStrategy.PRODUCE_IF_ALL_SPACE_AVAIL

        self._production_time_sec = None
        self.last_prod_s = None

        self._expertise_calculator = ExpertiseCalculator(schedule=expertise_schedule)

        self.current_exception = None
        self._last_perf = None

        self._metrics = Metrics()

        self._async_worker = AsyncWorker(self.update, start_on_init=start_on_init, id=f"ASYNC_{self.id}")

    def __repr__(self):
        return str(self)

    def __str__(self):
        exc = f"<{str(type(self.current_exception).__name__)}>" if self.current_exception else ""
        return f"{self.id} [{round(self.expertise.PercExpert * 100, 1)}%], {[x.name for x in self.status]}, {self.stored_inputs_as_content}, {self.available_output_as_content} {exc}"

    def __hash__(self):
        return hash(self.id)

    def start_async(self):
        self._async_worker.start_async()

    def _async_loop(self):
        while True:
            self.update()
            time.sleep(.1)

    def update(self, time_perf: float = None):
        if time_perf is None:
            time_perf = time.perf_counter()

        if self._last_perf is None:
            self._last_perf = time_perf

        if not self.producing:
            self._try_start_producing(time_perf)
        elif self.production_complete(time_perf):
            self.finish_producing()
            self._expertise_calculator.increment_s_producting(time_perf - self._last_perf)
        else:
            logger.debug(f"station_id {self.id}: producing...")
            self._expertise_calculator.increment_s_producting(time_perf - self._last_perf)

        # self._metrics.add_time_windows([TaggedTimeWindow(window=TimeWindow(start=self._last_perf, end=time_perf), tags=self.status)])
        self._last_perf = time_perf

    def progress(self, time_perf=None):
        if self._production_timer is None:
            return None

        if time_perf is None: time_perf = time.perf_counter()
        return self._production_timer.progress_at_time(time_perf)

    @property
    def producing(self):
        return True if self._production_timer is not None else False

    def _set_current_exception(self, e: Exception):
        if type(e) != type(self.current_exception):
            logger.warning(f"station_id {self.id}: {e}")

        self.current_exception = e


    def _try_start_producing(self, time_perf):
        try:
            self._start_producing(time_perf)
            self._set_current_exception(None)
        except (AtMaxCapacityException,
                OutputStorageToFullToProduceException,
                NotEnoughInputToProduceException,
                InvalidInputToAddToStationException) as e:
            self._set_current_exception(e)

    def _start_producing(self, time_perf: float = None):
        # verify have capacity to produce
        if self.producing:
            raise AtMaxCapacityException()

        # check if room for outputs to be produced
        self._raise_if_no_room_for_outputs()

        # check if enough input to produce
        self._raise_if_not_enough_inputs()

        # consume inputs
        self._consume_input()

        # get the production time
        self._production_time_sec = self._production_time_sec_callback() * (
                    1 - self._expertise_calculator.CurrentTimeReductionPerc)

        # update last prod time
        self.last_prod_s = self._production_time_sec

        # start the timer
        if time_perf is None: time_perf = time.perf_counter()
        self._production_timer = TimedDecay(time_ms=int(self._production_time_sec * 1000),
                                            start_perf=time_perf)

        # raise event
        evnts.raise_event_production_started_at_station(args=evnts.OnProductionStartedAtStationEventArgs(
            station=self
        ))

        logger.info(f"station_id {self.id}: Production Started")

    def _raise_if_no_room_for_outputs(self):
        space_minus_prod_run = self.output_space_minus_production_run
        open_space = self.space_for_output
        if self.production_strategy == StationProductionStrategy.PRODUCE_IF_ALL_SPACE_AVAIL and \
                not all(x >= 0 for x in space_minus_prod_run.values()):
            raise OutputStorageToFullToProduceException()
        elif self.production_strategy == StationProductionStrategy.PRODUCE_IF_ANY_SPACE_AVAIL and \
                not any(x > 0 for x in open_space.values()):
            raise OutputStorageToFullToProduceException()
        elif self.production_strategy not in [StationProductionStrategy.PRODUCE_IF_ANY_SPACE_AVAIL,
                                              StationProductionStrategy.PRODUCE_IF_ALL_SPACE_AVAIL]:
            raise NotImplementedError(f"Production Strategy: {self.production_strategy} is unrecognized for producing")

    def _raise_if_not_enough_inputs(self):
        stored = self.stored_inputs
        for input_req in self._input_reqs:
            key = (input_req.content.resource, input_req.content.uom)
            if stored.get(key, 0.0) < input_req.content.qty:
                raise NotEnoughInputToProduceException()

    def add_input(self, inputs: List[dcs.ContainerContent]):
        with threading.Lock():
            for input in inputs:
                key = (input.resource, input.uom)
                if key not in self._input_loc_ids:
                    raise InvalidInputToAddToStationException()
                self._input_storage.add_content_to_container_at_location(
                    loc_id=self._input_loc_ids[key],
                    contents=[input]
                )
                logger.info(f"station_id {self.id}: Content added: {input}")

    def _consume_input(self):
        with threading.Lock():
            for input_req in self._input_reqs:
                key = (input_req.content.resource, input_req.content.uom)
                self._input_storage.remove_content_from_container_at_location(
                    loc_id=self._input_loc_ids[key],
                    content=input_req.content
                )

    @property
    def available_output(self) -> Dict[ResourceUomKey, float]:
        return self._output_storage.InventoryByResourceUom

    @property
    def available_output_as_content(self) -> List[dcs.ContainerContent]:
        return self.resource_uom_float_nested_to_content(self.available_output)

    def remove_output(self, content: List[dcs.ContainerContent]) -> List[dcs.ContainerContent]:
        with threading.Lock():
            removed = []
            for c in content:
                key = (c.resource, c.uom)
                self._output_storage.remove_content_from_container_at_location(
                    loc_id=self._output_loc_ids[key],
                    content=c
                )
                removed.append(c)
                logger.info(f"station_id {self.id}: Content removed: {content}")

            return removed

    def reset_production(self):
        self._production_time_sec = None
        self._production_timer = None

    # ---------- persistence ----------
    #
    # Satisfies a consuming framework's to_state/apply_state protocol
    # structurally: this class implements the two methods and imports nothing to
    # do it, so persisting a Station creates no dependency on whatever is doing
    # the persisting.
    #
    # The line drawn throughout is state vs. definition. A Station is *built*
    # from its recipe -- input_reqs, output, the production-time callback, the
    # expertise schedule -- and *holds* what is in its stores and how far the
    # current run has got. Only the second half is written here; the first half
    # is rebuilt by whatever constructed this station the first time, from the
    # same recipe it used then.

    STATE_VERSION = 1

    def to_state(self) -> dict:
        """Everything play changed about this station.

        `_last_perf` and the run timer are written raw, in the caller's own clock.
        That is meaningful precisely because `update(time_perf=...)` lets the
        caller own the clock: a consumer driving this from a persisted accumulator
        restores that accumulator alongside this state, and the run resumes at the
        exact point it stopped. A station being driven from `time.perf_counter()`
        instead has no such guarantee -- perf_counter's origin is arbitrary per
        process -- and its run will read as long finished on load.
        """
        expertise = self._expertise_calculator._expertise_args
        return {
            STATE_VERSION_KEY: self.STATE_VERSION,
            'inputs': _contents_to_state(self.stored_inputs),
            'outputs': _contents_to_state(self.available_output),
            'production_time_sec': self._production_time_sec,
            'last_prod_s': self.last_prod_s,
            'last_perf': self._last_perf,
            'timer': ({'time_ms': self._production_timer.time_ms,
                       'start_perf': self._production_timer.start_perf}
                      if self._production_timer is not None else None),
            'expertise': {'n_runs': expertise.n_runs,
                          'accumulated_s': expertise.accumulated_s,
                          'exp': expertise.exp},
        }

    def apply_state(self, state: dict):
        """Replaces stores, run and expertise with the saved ones.

        Stores are emptied first: a station constructed from its recipe may
        already hold whatever its consumer put there on the way past, and a merge
        would leave it holding that plus the save.
        """
        version = state.get(STATE_VERSION_KEY)
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError(f"Station '{self.id}' state carries no usable "
                             f"'{STATE_VERSION_KEY}' version")
        if version > self.STATE_VERSION:
            raise ValueError(f"Station '{self.id}' state is version {version}, but this "
                             f"build understands up to {self.STATE_VERSION}")

        self._empty_store(self._input_storage, self._input_loc_ids, self.stored_inputs)
        self._empty_store(self._output_storage, self._output_loc_ids, self.available_output)

        self._fill_store(self._input_storage, self._input_loc_ids, state.get('inputs', []))
        self._fill_store(self._output_storage, self._output_loc_ids, state.get('outputs', []))

        self._production_time_sec = state.get('production_time_sec')
        self.last_prod_s = state.get('last_prod_s')
        self._last_perf = state.get('last_perf')

        timer = state.get('timer')
        self._production_timer = (
            TimedDecay(time_ms=timer['time_ms'], start_perf=timer['start_perf'])
            if timer is not None else None)

        # Rebuilt through the public increments on a fresh calculator rather than
        # by assigning its args, so the only reach into ExpertiseCalculator's
        # internals is the read in to_state.
        saved = state.get('expertise') or {}
        calculator = ExpertiseCalculator(schedule=self._expertise_calculator.schedule)
        calculator.increment_n_runs(saved.get('n_runs', 0))
        calculator.increment_s_producting(saved.get('accumulated_s', 0))
        calculator.increment_exp(saved.get('exp', 0))
        self._expertise_calculator = calculator

        self.current_exception = None

    def _empty_store(self, storage: Storage, loc_ids: Dict[ResourceUomKey, str],
                     held: Dict[ResourceUomKey, float]):
        for key, qty in list(held.items()):
            if qty > 0 and key in loc_ids:
                storage.remove_content_from_container_at_location(
                    loc_id=loc_ids[key],
                    content=dcs.ContainerContent(resource=key[0], uom=key[1], qty=qty))

    def _fill_store(self, storage: Storage, loc_ids: Dict[ResourceUomKey, str],
                    entries: List[dict]):
        for entry in entries:
            key = _resolve_key(loc_ids, entry['resource'], entry['uom'])
            if key is None:
                logger.warning(f"station_id {self.id}: saved {entry['qty']} "
                               f"{entry['resource']} has no slot in this station's recipe "
                               f"any more -- dropped")
                continue
            if entry['qty'] <= 0:
                continue
            storage.add_content_to_container_at_location(
                loc_id=loc_ids[key],
                contents=[dcs.ContainerContent(resource=key[0], uom=key[1], qty=entry['qty'])])

    def finish_producing(self):
        # generate outputs
        with threading.Lock():
            output_space = self.space_for_output
            for output in self._output:
                key = (output.content.resource, output.content.uom)
                qty = min(output_space[key], output.content.qty)
                if qty == 0:
                    continue
                self._output_storage.add_content_to_container_at_location(
                    loc_id=self._output_loc_ids[key],
                    contents=[dcs.ContainerContent(resource=output.content.resource, uom=output.content.uom, qty=qty)]
                )
                logger.info(f"station_id {self.id}: Content produced: {output.content}")

        # reset production
        self.reset_production()

        # update expertise
        self._expertise_calculator.increment_n_runs()

        # raise event
        evnts.raise_event_production_finished_at_station(args=evnts.OnProductionFinishedAtStationEventArgs(
            station=self
        ))

    def production_complete(self, time_perf) -> bool:
        if self._production_timer and self._production_timer.EndTime and time_perf > self._production_timer.EndTime:
            return True
        return False

    @property
    def short_inputs(self) -> List[dcs.ContainerContent]:
        short = []
        stored = self.stored_inputs
        for input in self._input_reqs:
            key = (input.content.resource, input.content.uom)
            stored_qty = stored.get(key, 0.0)
            if stored_qty < input.content.qty:
                short.append(dcs.ContainerContent(resource=input.content.resource, uom=input.content.uom, qty=input.content.qty - stored_qty))

        return short

    @property
    def space_for_input(self) -> Dict[ResourceUomKey, float]:
        stored = self.stored_inputs
        return {(defin.content.resource, defin.content.uom): defin.storage_capacity - stored.get((defin.content.resource, defin.content.uom), 0.0)
                for defin in self._input_reqs}

    @property
    def space_for_output(self) -> Dict[ResourceUomKey, float]:
        stored = self.available_output
        return {(defin.content.resource, defin.content.uom): defin.storage_capacity - stored.get((defin.content.resource, defin.content.uom), 0.0)
                for defin in self._output}

    @property
    def input_reqs(self):
        return self._input_reqs

    @property
    def outputs(self):
        return self._output

    @property
    def production_timer_sec_callback(self):
        return self._production_time_sec_callback

    @property
    def stored_inputs(self) -> Dict[ResourceUomKey, float]:
        return self._input_storage.InventoryByResourceUom

    @property
    def stored_inputs_as_content(self) -> List[dcs.ContainerContent]:
        return self.resource_uom_float_nested_to_content(self.stored_inputs)

    def resource_uom_float_nested_to_content(self,
                                             resource_uom_float_nested: Dict[ResourceUomKey, float]) -> List[dcs.ContainerContent]:
        return [dcs.ContainerContent(resource=resource_uom[0], uom=resource_uom[1], qty=qty) for resource_uom, qty in resource_uom_float_nested.items()]

    @property
    def output_space_minus_production_run(self) -> Dict[ResourceUomKey, float]:
        output_space = self.space_for_output
        ret = {key: qty - next(x.content.qty
                               for x in self.outputs if (x.content.resource, x.content.uom) == key)
               for key, qty in output_space.items()}
        return ret

    @property
    def status(self) -> List[StationStatus]:
        ret = []

        if self.producing:
            ret.append(StationStatus.PRODUCING)
        else:
            ret.append(StationStatus.IDLE)

        if len(self.short_inputs) > 0:
            ret.append(StationStatus.STARVED)

        out_space_minus_production_run = self.output_space_minus_production_run
        if any([x < 0 for x in out_space_minus_production_run.values()]):
            ret.append(StationStatus.FULL)

        return ret

    @property
    def expertise(self):
        return self._expertise_calculator

    @property
    def started(self):
        return self._async_worker.started

    @property
    def metrics(self):
        return self._metrics

    @property
    def InputStorageState(self) -> Storage:
        return self._input_storage

    @property
    def OutputStorageState(self) -> Storage:
        return self._output_storage

    @property
    def AsyncStarted(self) -> bool:
        return self._async_worker.started


def station_factory(station_template: Station,
                    id: str = None,
                    start_on_init: bool = False,
                    expertise_schedule: ExpertiseSchedule = None) -> Station:
    expertise_schedule = expertise_schedule or (station_template.expertise.schedule)

    return Station(
        id=id,
        input_reqs=station_template.input_reqs,
        output=station_template.outputs,
        production_timer_sec_callback=station_template.production_timer_sec_callback,
        type=station_template.type,
        start_on_init=start_on_init,
        expertise_schedule=expertise_schedule,
        production_strategy=station_template.production_strategy
    )


if __name__ == "__main__":
    from tests.station_manifest import STATIONS, StationType

    logging.basicConfig(level=logging.INFO)
    s_template = STATIONS[StationType.RAW_1]
    station = station_factory(s_template, start_on_init=False, id=f"{s_template.id}_0")

    while True:
        time.sleep(.5)
        station.update()

        to_remove = []
        space_for_output = station.space_for_output
        for (resource, uom), qty in station.available_output.items():
            defin = next(x for x in station.outputs if x.content.resource == resource and x.content.uom == uom)
            if qty > 0.75 * defin.storage_capacity:
                to_remove.append(dcs.ContainerContent(resource=resource, uom=uom, qty=qty))
        station.remove_output(to_remove)

        shorts = station.short_inputs
        if len(shorts) > 0:
            time.sleep(4)
            station.add_input(shorts)
