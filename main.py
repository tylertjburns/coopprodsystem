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
logging.getLogger('coopprodsystem.station').setLevel(logging.CRITICAL)

deh = DummyEventHandler()
pl = ProductionLine(
    init_stations=[(x, Vector2(rnd.randint(0, 10), rnd.randint(0, 10))) for x in STATIONS.values()],
    init_relationship_map={
        STATIONS[StationType.DUMMY_3]: [
            (STATIONS[StationType.DUMMY_1], [ResourceUoM(skus.sku_c, UoM(UoMType.EACH))]),
            (STATIONS[StationType.DUMMY_2], [ResourceUoM(skus.sku_f, UoM(UoMType.EACH))])
        ],
        STATIONS[StationType.DUMMY_1]: [
            (STATIONS[StationType.RAW_1], [ResourceUoM(skus.sku_a, UoM(UoMType.EACH))]),
            (STATIONS[StationType.RAW_2], [ResourceUoM(skus.sku_b, UoM(UoMType.EACH))])
        ],
        STATIONS[StationType.DUMMY_2]: [
            (STATIONS[StationType.RAW_1], [ResourceUoM(skus.sku_d, UoM(UoMType.EACH))]),
            (STATIONS[StationType.RAW_2], [ResourceUoM(skus.sku_e, UoM(UoMType.EACH))])
        ]

    },
    start_on_init=True
)

# pl = ProductionLine(
#     init_stations=[(STATIONS[x], Vector2(rnd.randint(0, 10), rnd.randint(0, 10))) for x in [StationType.RAW_1, StationType.RAW_2, StationType.DUMMY_2]],
#     init_relationship_map={
#         STATIONS[StationType.DUMMY_2]: [
#             (STATIONS[StationType.RAW_1], [ResourceUoM(skus.sku_d, UoM(UoMType.EACH))]),
#             (STATIONS[StationType.RAW_2], [ResourceUoM(skus.sku_e, UoM(UoMType.EACH))])
#         ]
#     },
#     start_on_init=True
# )


generated = []
s1_timer = None
s2_timer = None
s3_timer = None
while True:
    #display
    pl.print_state()

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


