from coopprodsystem.factory import Station, station_resource_def_EA_uom, StationProductionStrategy
import sku_manifest as skus
from cooptools.coopEnum import CoopEnum
from enum import auto
from typing import Dict

class StationType(CoopEnum):
    DUMMY_1 = auto()
    DUMMY_2 = auto()
    DUMMY_3 = auto()
    RAW_1 = auto()
    RAW_2 = auto()


outputs = [
    station_resource_def_EA_uom(content_resource=skus.sku_a, content_qty=3, storage_capacity=21),
    station_resource_def_EA_uom(content_resource=skus.sku_d, content_qty=3, storage_capacity=21),
]
r1 = Station(id=StationType.RAW_1.name, input_reqs=[], output=outputs, production_timer_sec_callback=lambda: 3,start_on_init=True, production_strategy=StationProductionStrategy.PRODUCE_IF_ANY_SPACE_AVAIL)

outputs = [
    station_resource_def_EA_uom(content_resource=skus.sku_b, content_qty=3, storage_capacity=21),
    station_resource_def_EA_uom(content_resource=skus.sku_e, content_qty=3, storage_capacity=21),
]
r2 = Station(id=StationType.RAW_2.name, input_reqs=[], output=outputs, production_timer_sec_callback=lambda: 3,start_on_init=True, production_strategy=StationProductionStrategy.PRODUCE_IF_ANY_SPACE_AVAIL)

input_reqs = [
    station_resource_def_EA_uom(content_resource=skus.sku_a, content_qty=5, storage_capacity=10),
    station_resource_def_EA_uom(content_resource=skus.sku_b, content_qty=1, storage_capacity=5),
]
outputs = [
    station_resource_def_EA_uom(content_resource=skus.sku_c, content_qty=3, storage_capacity=3),
]
s1 = Station(id=StationType.DUMMY_1.name, input_reqs=input_reqs, output=outputs, production_timer_sec_callback=lambda: 3,start_on_init=True)

input_reqs = [
    station_resource_def_EA_uom(content_resource=skus.sku_d, content_qty=5, storage_capacity=10),
    station_resource_def_EA_uom(content_resource=skus.sku_e, content_qty=1, storage_capacity=5),
]
outputs = [
    station_resource_def_EA_uom(content_resource=skus.sku_f, content_qty=3, storage_capacity=3),
]
s2 = Station(id=StationType.DUMMY_2.name, input_reqs=input_reqs, output=outputs, production_timer_sec_callback=lambda: 3,start_on_init=True)

input_reqs = [
    station_resource_def_EA_uom(content_resource=skus.sku_c, content_qty=5, storage_capacity=10),
    station_resource_def_EA_uom(content_resource=skus.sku_f, content_qty=1, storage_capacity=5),
]
outputs = [
    station_resource_def_EA_uom(content_resource=skus.sku_g, content_qty=3, storage_capacity=3),
]
s3 = Station(id=StationType.DUMMY_3.name,
             input_reqs=input_reqs,
             output=outputs,
             production_timer_sec_callback=lambda: 3,
             start_on_init=True)


STATIONS: Dict[StationType, Station] = {
    StationType.DUMMY_1: s1,
    StationType.DUMMY_2: s2,
    StationType.DUMMY_3: s3,
    StationType.RAW_1: r1,
    StationType.RAW_2: r2

}
