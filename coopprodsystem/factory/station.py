import time
import threading
import uuid

from coopprodsystem.my_dataclasses import Content, content_factory, Resource, UoM
from typing import List, Optional, Callable, Dict, Tuple
from cooptools.timedDecay import Timer
from coopprodsystem.storage import Storage, Location
import logging
import traceback
import coopprodsystem.events as evnts
from .stationResourceDefinition import StationResourceDefinition
from cooptools.common import flattened_list_of_lists
from coopprodsystem.factory.stationStatus import StationStatus

logger = logging.getLogger('station')

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


class Station:
    def __init__(self,
                 input_reqs: List[StationResourceDefinition],
                 output: List[StationResourceDefinition],
                 production_timer_sec_callback: ProductionTimeSecCallback,
                 id: str = None,
                 type: str = None,
                 start_on_init: bool = False
                 ):
        self.id = id if id else uuid.uuid4()
        self.type = type
        self._input_reqs = input_reqs
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

        self._refresh_thread = None
        if start_on_init:
            self.start_refresh_thread()

    def start_refresh_thread(self):
        self._refresh_thread = threading.Thread(target=self._async_loop, daemon=True)
        self._refresh_thread.start()

    def _async_loop(self):
        while True:
            if not self.producing:
                self._try_start_producing()
            elif self.production_complete:
                self.finish_producing()
            else:
                logger.info(f"station_id {self.id}: producing...")

            time.sleep(.1)

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
        except (AtMaxCapacityException,
                OutputStorageToFullToProduceException,
                NotEnoughInputToProduceException,
                InvalidInputToAddToStationException) as e:
            logger.warning(f"station_id {self.id}: {e}")
        except Exception as e:
            logger.error(f"station_id {self.id}: {e} ->"
                         f"\n{traceback.format_exc()}")

    def _start_producing(self):
        # verify have capacity to produce
        if self.producing:
            raise AtMaxCapacityException()

        # check if room for outputs to be produced
        for output in self._output:
            stored_out = self._output_storage.qty_of_resource_uom(resource=output.content.resource,
                                                                  uom_type=output.content.uom.type)
            if stored_out + output.content.qty > output.storage_capacity:
                raise OutputStorageToFullToProduceException()

        # check if enough input to produce
        for input_req in self._input_reqs:
            stored_in = self._input_storage.qty_of_resource_uom(resource=input_req.content.resource,
                                                                uom_type=input_req.content.uom.type)
            if stored_in < input_req.content.qty:
                raise NotEnoughInputToProduceException()

        # consume inputs
        self._consume_input()

        # get the production time
        self._production_time_sec = self._production_time_sec_callback()

        # start the timer
        self._production_timer = Timer(int(self._production_time_sec * 1000), start_on_init=True)

        # raise event
        evnts.raise_event_production_started_at_station(args=evnts.OnProductionStartedAtStationEventArgs(
            station_id=self.id
        ))

        logger.info(f"station_id {self.id}: Production Started")

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
    def available_output(self) -> Dict[Resource, Dict[UoM, float]]:
        return self._output_storage.inventory_by_resource

    @property
    def available_output_as_content(self) -> List[Content]:
        return self.resource_uom_float_nested_to_content(self.available_output)

    def remove_output(self, content: List[Content]) -> List[Content]:
        with threading.Lock():
            removed = []
            for c in content:
                rmvd = self._output_storage.remove_content(content_factory(c))
                removed.append(rmvd)
                logger.info(f"station_id {self.id}: Content removed: {content}")

            return removed

    def reset_production(self):
        self._production_time_sec = None
        self._production_timer = None

    def finish_producing(self):
        # generate outputs
        with threading.Lock():
            for output in self._output:
                self._output_storage.add_content(content_factory(output.content))
                logger.info(f"station_id {self.id}: Content produced: {output.content}")

        # reset production
        self.reset_production()

        # raise event
        evnts.raise_event_production_finished_at_station(args=evnts.OnProductionFinishedAtStationEventArgs(
            station_id=self.id
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
            stored = self._input_storage.qty_of_resource_uom(input.content.resource, input.content.uom.type)
            if stored < input.content.qty:
                short.append(content_factory(input.content, qty=input.content.qty - stored))

        return short

    @property
    def space_for_input(self) -> Dict[Resource, Dict[UoM, float]]:
        return self._input_storage.space_for_resource_uom(
            [(defin.content.resource, defin.content.uom) for defin in self._output]
        )

    @property
    def space_for_output(self) -> Dict[Resource, Dict[UoM, float]]:
        return self._output_storage.space_for_resource_uom(
            [(defin.content.resource, defin.content.uom) for defin in self._output]
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
    def stored_inputs(self) -> Dict[Resource, Dict[UoM, float]]:
        return self._input_storage.inventory_by_resource

    @property
    def stored_inputs_as_content(self) -> List[Content]:
        return self.resource_uom_float_nested_to_content(self.stored_inputs)

    def resource_uom_float_nested_to_content(self,
                                             resource_uom_float_nested: Dict[Resource, Dict[UoM, float]]) -> List[Content]:
        flat_avail = flattened_list_of_lists(
            [[Content(resource, uom, float) for uom, float in uom_amt_dict.items()] for resource, uom_amt_dict in
             resource_uom_float_nested.items()])

        return flat_avail

    def content_to_resource_uom_float_nested(self, resource_uom_float_nested: Dict[Resource, Dict[UoM, float]]) -> List[
        Content]:
        flat_avail = flattened_list_of_lists(
            [[(resource, uom, float) for uom, float in uom_amt_dict.items()] for resource, uom_amt_dict in
             resource_uom_float_nested.items()])

        return flat_avail

    @property
    def status(self) -> List[StationStatus]:
        ret = []

        if self.producing:
            ret.append(StationStatus.PRODUCING)
        else:
            ret.append(StationStatus.IDLE)

        if len(self.short_inputs) > 0:
            ret.append(StationStatus.STARVED)

        output_space = self.space_for_output
        out_space_flat = flattened_list_of_lists([[qty for uom, qty in uom_dict.items()] for resource, uom_dict in output_space.items()])
        if any([x==0 for x in out_space_flat]):
            ret.append(StationStatus.FULL)

        return ret

def station_factory(station_template: Station,
                    id: str = None,
                    start_on_init: bool = False) -> Station:
    return Station(
        id=id,
        input_reqs=station_template.input_reqs,
        output=station_template.outputs,
        production_timer_sec_callback=station_template.production_timer_sec_callback,
        type=station_template.type,
        start_on_init=start_on_init
    )


if __name__ == "__main__":
    from station_manifest import STATIONS, StationType

    logging.basicConfig(level=logging.INFO)
    station = STATIONS[StationType.DUMMY_1]

    while True:
        time.sleep(.5)

        if len(station.available_output) > 0:
            time.sleep(3)
            station.remove_output(station.available_output[0])

        shorts = station.short_inputs
        if len(shorts) > 0:
            time.sleep(4)
            station.add_input(shorts)

