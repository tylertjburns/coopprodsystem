from coopprodsystem.factory import Station, station_resource_def_EA_uom
import sku_manifest as skus
from cooptools.coopEnum import CoopEnum
from enum import auto

class StationType(CoopEnum):
    DUMMY_1 = auto()
    DUMMY_2 = auto()
    DUMMY_3 = auto()


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


STATIONS = {
    StationType.DUMMY_1: s1,
    StationType.DUMMY_2: s2,
    StationType.DUMMY_3: s3,

}
