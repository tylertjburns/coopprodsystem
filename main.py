from dummyEventHandler import DummyEventHandler
import time
import logging
from station_manifest import STATIONS, StationType
from coopprodsystem.factory.productionLine import transfer_station

format = '%(asctime)s [%(levelname)s]: %(name)s -- %(message)s (%(filename)s:%(lineno)d)'
logging.basicConfig(format=format, level=logging.INFO)
logging.getLogger('station').setLevel(logging.CRITICAL)

deh = DummyEventHandler()

generated = []
s1_timer = None
s2_timer = None
s3_timer = None
while True:
    print(STATIONS[StationType.DUMMY_1].progress)
    print(STATIONS[StationType.DUMMY_2].progress)
    print(STATIONS[StationType.DUMMY_3].progress)

    # s1 short
    shorts = STATIONS[StationType.DUMMY_1].short_inputs
    if len(shorts) > 0 and s1_timer is None:
        s1_timer = time.perf_counter()
    elif s1_timer and time.perf_counter() - s1_timer > 4:
        STATIONS[StationType.DUMMY_1].add_input(shorts)
        s1_timer = None

    # s2 short
    shorts = STATIONS[StationType.DUMMY_2].short_inputs
    if len(shorts) > 0 and s2_timer is None:
        s2_timer = time.perf_counter()
    elif s2_timer and time.perf_counter() - s2_timer > 4:
        STATIONS[StationType.DUMMY_2].add_input(shorts)
        s2_timer = None

    # available to move?
    transfer_station(from_s=STATIONS[StationType.DUMMY_1], to_s=STATIONS[StationType.DUMMY_3], delay_s=3)
    transfer_station(from_s=STATIONS[StationType.DUMMY_2], to_s=STATIONS[StationType.DUMMY_3], delay_s=2)

    # s3 full
    if len(STATIONS[StationType.DUMMY_3].available_output) > 0 and s3_timer is None:
        s3_timer = time.perf_counter()
    elif s3_timer and time.perf_counter() - s3_timer > 3:
        content_removed = STATIONS[StationType.DUMMY_3].remove_output(STATIONS[StationType.DUMMY_3].available_output_as_content)
        generated += content_removed
        s3_timer = None

    # epoch
    print(sum(x.qty for x in generated))
    time.sleep(.5)


