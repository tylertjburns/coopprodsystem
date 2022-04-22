from dummyEventHandler import DummyEventHandler
import time
import logging
from station_manifest import STATIONS, StationType
from coopprodsystem.factory.productionLine import transfer_station, ProductionLine
from coopprodsystem.my_dataclasses import ResourceUoM, UoM, UoMType
from coopstructs.vectors import Vector2
import random as rnd
import sku_manifest as skus

format = '%(asctime)s [%(levelname)s]: %(name)s -- %(message)s (%(filename)s:%(lineno)d)'
logging.basicConfig(format=format, level=logging.INFO)
logging.getLogger('station').setLevel(logging.CRITICAL)

deh = DummyEventHandler()
pl = ProductionLine(
    init_stations=[(x, Vector2(rnd.randint(0, 10), rnd.randint(0, 10))) for x in STATIONS.values()],
    init_relationship_map={
        STATIONS[StationType.DUMMY_3]: [(STATIONS[StationType.DUMMY_1], [ResourceUoM(skus.sku_c, UoM(UoMType.EACH))]),
                                        (STATIONS[StationType.DUMMY_2], [ResourceUoM(skus.sku_f, UoM(UoMType.EACH))])],
    },
    start_on_init=True
)


generated = []
s1_timer = None
s2_timer = None
s3_timer = None
while True:
    print(STATIONS[StationType.DUMMY_1].id, round(STATIONS[StationType.DUMMY_1].progress or 0, 2), STATIONS[StationType.DUMMY_1].status)
    print(STATIONS[StationType.DUMMY_2].id, round(STATIONS[StationType.DUMMY_2].progress or 0, 2), STATIONS[StationType.DUMMY_2].status)
    print(STATIONS[StationType.DUMMY_3].id, round(STATIONS[StationType.DUMMY_3].progress or 0, 2), STATIONS[StationType.DUMMY_3].status)

    # Hack to keep s1 stocked with inputs
    shorts = STATIONS[StationType.DUMMY_1].short_inputs
    if len(shorts) > 0 and s1_timer is None:
        s1_timer = time.perf_counter()
    elif s1_timer and time.perf_counter() - s1_timer > 4:
        STATIONS[StationType.DUMMY_1].add_input(shorts)
        s1_timer = None

    # Hack to keep s2 stocked with inputs
    shorts = STATIONS[StationType.DUMMY_2].short_inputs
    if len(shorts) > 0 and s2_timer is None:
        s2_timer = time.perf_counter()
    elif s2_timer and time.perf_counter() - s2_timer > 4:
        STATIONS[StationType.DUMMY_2].add_input(shorts)
        s2_timer = None

    # Hack to remove content from s3 when there is output
    if len(STATIONS[StationType.DUMMY_3].available_output) > 0 and s3_timer is None:
        s3_timer = time.perf_counter()
    elif s3_timer and time.perf_counter() - s3_timer > 3:
        content_removed = STATIONS[StationType.DUMMY_3].remove_output(STATIONS[StationType.DUMMY_3].available_output_as_content)
        generated += content_removed
        s3_timer = None



    # epoch
    print(sum(x.qty for x in generated))
    time.sleep(1)


