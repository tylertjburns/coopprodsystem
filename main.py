from dummyEventHandler import DummyEventHandler
import time
import logging
from tests.station_manifest import STATIONS, StationType
from coopprodsystem.factory import ProductionLine, Station, station_factory, ByRunsExpertiseSchedule
from coopstorage.my_dataclasses import ResourceUoM, UoM
from coopstructs.vectors import Vector2
import random as rnd
import tests.sku_manifest as skus
from tests.uom_manifest import each

format = '%(asctime)s [%(levelname)s]: %(name)s -- %(message)s (%(filename)s:%(lineno)d)'
logging.basicConfig(format=format, level=logging.INFO)
logging.getLogger('station').setLevel(logging.CRITICAL)
logging.getLogger('coopprodsystem.station').setLevel(logging.CRITICAL)
logging.getLogger('coopprodsystem.productionLine').setLevel(logging.CRITICAL)
logging.getLogger('coopstorage').setLevel(logging.CRITICAL)

deh = DummyEventHandler()
expertise_schedule = ByRunsExpertiseSchedule(runs_until_expert=1000, max_time_reduction_perc=.33)

relationship_mapper = {
    StationType.DUMMY_3: [
            (StationType.DUMMY_1, [ResourceUoM(skus.sku_c, each)]),
            (StationType.DUMMY_2, [ResourceUoM(skus.sku_f, each)])
    ],
    StationType.DUMMY_1: [
        (StationType.RAW_1, [ResourceUoM(skus.sku_a, each)]),
        (StationType.RAW_2, [ResourceUoM(skus.sku_b, each)])
    ],
    StationType.DUMMY_2: [
        (StationType.RAW_1, [ResourceUoM(skus.sku_d, each)]),
        (StationType.RAW_2, [ResourceUoM(skus.sku_e, each)])
    ]
}

stations_pos = [(station_factory(x,
                                 id=f"{x.id}",
                                 expertise_schedule=expertise_schedule), Vector2(rnd.randint(0, 10), rnd.randint(0, 10))) for x in STATIONS.values()]
relationship_map = {next(station for station, _ in stations_pos if station.type == dest_type.name):
                        [(next(station for station, _ in stations_pos if station.type == srs[0].name), srs[1]) for srs in srss]
                    for dest_type, srss in relationship_mapper.items()}

pl = ProductionLine(
    init_stations=stations_pos,
    init_relationship_map=relationship_map,
    start_on_init=True
)


generated = []
s1_timer = None
s2_timer = None
s3_timer = None
while True:
    #display
    pl.print_state()

    # Hack to remove content from s3 when there is output
    end_station = next(station for name, station in pl.Stations.items() if station.type == StationType.DUMMY_3.name)

    if len(end_station.available_output) > 0 and s3_timer is None:
        s3_timer = time.perf_counter()
    elif s3_timer and time.perf_counter() - s3_timer > 3:
        content_removed = end_station.remove_output(end_station.available_output_as_content)
        generated += content_removed
        s3_timer = None

    # epoch
    print(sum(x.qty for x in generated))
    time.sleep(1)


