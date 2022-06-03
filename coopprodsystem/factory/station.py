import time
import threading
import uuid

from coopprodsystem.my_dataclasses import Content, content_factory, ResourceUoM
from typing import List, Optional, Callable, Dict
from cooptools.timedDecay import Timer
from coopprodsystem.storage.storage import Storage, Location
import logging
import coopprodsystem.events as evnts
from coopprodsystem.factory.stationResourceDefinition import StationResourceDefinition
from coopprodsystem.factory.stationStatus import StationStatus
from cooptools.coopEnum import CoopEnum
from enum import auto
from coopprodsystem.factory.expertiseSchedules import ExpertiseSchedule, ExpertiseCalculator
from cooptools.coopthreading import AsyncWorker
from cooptools.timeWindow import TimeWindow
from cooptools.metrics import Metrics

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
                                uom_capacities={x.content.uom.type: x.storage_capacity},
                                resource_limitations=[x.content.resource]) for ii, x in enumerate(input_reqs)])
        self._output_storage = Storage(
            id=f"{self.id}_output",
            locations=[Location(id=f"{self.id}_{ii}",
                                uom_capacities={x.content.uom.type: x.storage_capacity},
                                resource_limitations=[x.content.resource]) for ii, x in enumerate(output)])
        self._production_time_sec_callback = production_timer_sec_callback
        self._production_timer: Optional[Timer] = None
        self.production_strategy: StationProductionStrategy = production_strategy or StationProductionStrategy.PRODUCE_IF_ALL_SPACE_AVAIL

        self._production_time_sec = None
        self.last_prod_s = None

        self._expertise_calculator = ExpertiseCalculator(schedule=expertise_schedule)

        self.current_exception = None
        self._refresh_thread = None

        self._last_perf = None

        self._metrics = Metrics()

        self._async_worker = AsyncWorker(self.update, start_on_init=start_on_init, id=f"ASYNC_{self.id}")
        # if start_on_init:
        #     self.start_async()

    def __repr__(self):
        return str(self)

    def __str__(self):
        exc = f"<{str(type(self.current_exception).__name__)}>" if self.current_exception else ""
        return f"{self.id}, {[x.name for x in self.status]}, {round(self.progress or 0, 2)}, {self.stored_inputs_as_content}, {self.available_output_as_content} {exc}"

    def __hash__(self):
        return hash(self.id)

    def start_async(self):
        self._refresh_thread = threading.Thread(target=self._async_loop, daemon=True)
        self._last_perf = time.perf_counter()
        self._refresh_thread.start()

    def _async_loop(self):
        while True:
            self.update()
            time.sleep(.1)

    def update(self):

        t_now = time.perf_counter()

        if not self.producing:
            self._try_start_producing()
        elif self.production_complete:
            self.finish_producing()
            self._expertise_calculator.increment_s_producting(t_now - self._last_perf)
        else:
            logger.info(f"station_id {self.id}: producing...")
            self._expertise_calculator.increment_s_producting(t_now - self._last_perf)


        self._metrics.add_time_windows([TimeWindow(start=self._last_perf, end=t_now, tags=self.status)])
        self._last_perf = t_now

    @property
    def progress(self):
        if self._production_timer is None:
            return None

        return self._production_timer.progress

    @property
    def producing(self):
        return True if self._production_timer is not None else False

    def _try_start_producing(self):
        try:
            self._start_producing()
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

    def _start_producing(self):
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
        self._production_time_sec = self._production_time_sec_callback() * (1 - self._expertise_calculator.current_time_reduction_perc())

        # update last prod time
        self.last_prod_s = self._production_time_sec

        # start the timer
        self._production_timer = Timer(int(self._production_time_sec * 1000), start_on_init=True)

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
            stored_in = self._input_storage.qty_of_resource_uoms(resource_uoms=[input_req.content.resourceUoM])[input_req.content.resourceUoM]
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
        return self._output_storage.inventory_by_resource_uom

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

    @property
    def production_complete(self) -> bool:
        if self._production_timer and self._production_timer.finished:
            return True
        return False

    @property
    def short_inputs(self) -> List[Content]:
        short = []

        for input in self._input_reqs:
            stored = self._input_storage.qty_of_resource_uoms(resource_uoms=[input.content.resourceUoM])[input.content.resourceUoM]
            if stored < input.content.qty:
                short.append(content_factory(input.content, qty=input.content.qty - stored))

        return short

    @property
    def space_for_input(self) -> Dict[ResourceUoM, float]:
        return self._input_storage.space_for_resource_uom(
            [defin.content.resourceUoM for defin in self._input_reqs]
        )

    @property
    def space_for_output(self) -> Dict[ResourceUoM, float]:
        return self._output_storage.space_for_resource_uom(
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
        return self._input_storage.inventory_by_resource_uom

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

def station_factory(station_template: Station,
                    id: str = None,
                    start_on_init: bool = False) -> Station:
    return Station(
        id=id,
        input_reqs=station_template.input_reqs,
        output=station_template.outputs,
        production_timer_sec_callback=station_template.production_timer_sec_callback,
        type=station_template.type,
        start_on_init=start_on_init,
        expertise_schedule=station_template.expertise.schedule,
        production_strategy=station_template.production_strategy
    )


if __name__ == "__main__":
    from station_manifest import STATIONS, StationType

    logging.basicConfig(level=logging.INFO)
    station = STATIONS[StationType.DUMMY_1]

    while True:
        time.sleep(.5)

        if len(station.available_output) > 0:
            time.sleep(3)
            to_remove = [Content(resourceUoM=k, qty=v) for k, v in station.available_output.items()]
            station.remove_output(to_remove)

        shorts = station.short_inputs
        if len(shorts) > 0:
            time.sleep(4)
            station.add_input(shorts)

