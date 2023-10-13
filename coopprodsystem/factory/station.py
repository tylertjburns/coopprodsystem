import time
import threading
import uuid

from typing import List, Optional, Callable, Dict
from cooptools.timedDecay import Timer, TimedDecay
import logging
import coopprodsystem.events as evnts
from coopprodsystem.factory.stationResourceDefinition import StationResourceDefinition
from coopprodsystem.factory.stationStatus import StationStatus
from cooptools.coopEnum import CoopEnum
from enum import auto
from coopprodsystem.factory.expertiseSchedules import ExpertiseSchedule, ExpertiseCalculator
from cooptools.coopthreading import AsyncWorker
from cooptools.timeWindow import TaggedTimeWindow, TimeWindow
from cooptools.metrics import Metrics
from coopstorage.storage import Storage, Location, StorageState
from coopstorage.my_dataclasses import UoMCapacity, Content, content_factory, ResourceUoM

logger = logging.getLogger('coopprodsystem.station')

ProductionTimeSecCallback = Callable[[], float]


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
        self._input_storage = Storage(
            id=f"{self.id}_input",
            locations=[Location(id=f"{self.id}_{ii}",
                                uom_capacities=frozenset([UoMCapacity(x.content.uom, x.storage_capacity)]),
                                resource_limitations=frozenset([x.content.resource])) for ii, x in
                       enumerate(input_reqs)])
        self._output_storage = Storage(
            id=f"{self.id}_output",
            locations=[Location(id=f"{self.id}_{ii}",
                                uom_capacities=frozenset([UoMCapacity(x.content.uom, x.storage_capacity)]),
                                resource_limitations=frozenset([x.content.resource])) for ii, x in enumerate(output)])
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
            logger.info(f"station_id {self.id}: producing...")
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

    def _try_start_producing(self, time_perf):
        try:
            self._start_producing(time_perf)
            self.current_exception = None
        except (AtMaxCapacityException,
                OutputStorageToFullToProduceException,
                NotEnoughInputToProduceException,
                InvalidInputToAddToStationException) as e:
            self.current_exception = e
            logger.warning(f"station_id {self.id}: {e}")
        # except Exception as e:
        #     logger.error(f"station_id {self.id}: {e} ->"
        #                  f"\n{traceback.format_exc()}")

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
        # self._production_timer = Timer(int(self._production_time_sec * 1000), start_on_init=True)

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
        for input_req in self._input_reqs:
            stored_in = self._input_storage.state.qty_of_resource_uoms(resource_uoms=[input_req.content.resourceUoM])[
                input_req.content.resourceUoM]
            if stored_in < input_req.content.qty:
                raise NotEnoughInputToProduceException()

    def add_input(self, inputs: List[Content]):
        with threading.Lock():
            for input in inputs:
                if not any([x.content.match_resouce_uom(input) for x in self._input_reqs]):
                    raise InvalidInputToAddToStationException()
                self._input_storage.add_content(content_factory(input))
                logger.info(f"station_id {self.id}: Content added: {input}")

    def _consume_input(self):
        with threading.Lock():
            for input_req in self._input_reqs:
                self._input_storage.remove_content(content_factory(input_req.content))

    @property
    def available_output(self) -> Dict[ResourceUoM, float]:
        return self._output_storage.state.InventoryByResourceUom

    @property
    def available_output_as_content(self) -> List[Content]:
        return self.resource_uom_float_nested_to_content(self.available_output)

    def remove_output(self, content: List[Content]) -> List[Content]:
        with threading.Lock():
            removed = []
            for c in content:
                rmvd = self._output_storage.remove_content(c)
                removed.append(rmvd)
                logger.info(f"station_id {self.id}: Content removed: {content}")

            return removed

    def reset_production(self):
        self._production_time_sec = None
        self._production_timer = None

    def finish_producing(self):
        # generate outputs
        with threading.Lock():
            output_space = self.space_for_output
            for output in self._output:
                qty = min(output_space[output.content.resourceUoM], output.content.qty)
                if qty == 0:
                    continue
                self._output_storage.add_content(
                    content_factory(output.content, qty=qty)
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
    def short_inputs(self) -> List[Content]:
        short = []

        for input in self._input_reqs:
            stored = self._input_storage.state.qty_of_resource_uoms(resource_uoms=[input.content.resourceUoM])[
                input.content.resourceUoM]
            if stored < input.content.qty:
                short.append(content_factory(input.content, qty=input.content.qty - stored))

        return short

    @property
    def space_for_input(self) -> Dict[ResourceUoM, float]:
        return self._input_storage.state.space_for_resource_uom(
            [defin.content.resourceUoM for defin in self._input_reqs]
        )

    @property
    def space_for_output(self) -> Dict[ResourceUoM, float]:
        return self._output_storage.state.space_for_resource_uom(
            [defin.content.resourceUoM for defin in self._output]
        )

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
    def stored_inputs(self) -> Dict[ResourceUoM, float]:
        return self._input_storage.state.InventoryByResourceUom

    @property
    def stored_inputs_as_content(self) -> List[Content]:
        return self.resource_uom_float_nested_to_content(self.stored_inputs)

    def resource_uom_float_nested_to_content(self,
                                             resource_uom_float_nested: Dict[ResourceUoM, float]) -> List[Content]:
        return [Content(resource_uom, float) for resource_uom, float in resource_uom_float_nested.items()]

    def content_to_resource_uom_float_nested(self, content: List[Content]) -> Dict[ResourceUoM, float]:
        return {c.resourceUoM: c.qty for c in content}

    @property
    def output_space_minus_production_run(self) -> Dict[ResourceUoM, float]:
        output_space = self.space_for_output
        ret = {resource_uom: qty - next(x.content.qty
                                        for x in self.outputs if x.content.resourceUoM == resource_uom)
               for resource_uom, qty in output_space.items()}
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
        # return not self._refresh_thread is None
        return self._async_worker.started

    @property
    def metrics(self):
        return self._metrics

    @property
    def InputStorageState(self) -> StorageState:
        return self._input_storage.state

    @property
    def OutputStorageState(self) -> StorageState:
        return self._output_storage.state

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
    from coopprodsystem.factory import station_factory

    logging.basicConfig(level=logging.INFO)
    s_template = STATIONS[StationType.RAW_1]
    station = station_factory(s_template, start_on_init=False, id=f"{s_template.id}_0")

    while True:
        time.sleep(.5)
        station.update()

        to_remove = []
        for ru, qty in station.available_output.items():
            if qty > 0.75 * station.OutputStorageState.capacity_for_resource_uoms(resource_uoms=[ru])[ru]:
                to_remove.append(Content(resourceUoM=ru, qty=qty))
        station.remove_output(to_remove)

        shorts = station.short_inputs
        if len(shorts) > 0:
            time.sleep(4)
            station.add_input(shorts)

