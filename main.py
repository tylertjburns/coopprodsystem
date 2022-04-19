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
while True:
    # s1 short
    shorts = STATIONS[StationType.DUMMY_1].short_inputs
    if len(shorts) > 0:
        time.sleep(4)
        STATIONS[StationType.DUMMY_1].add_input(shorts)

    # s2 short
    shorts = STATIONS[StationType.DUMMY_2].short_inputs
    if len(shorts) > 0:
        time.sleep(4)
        STATIONS[StationType.DUMMY_2].add_input(shorts)

    # available to move?
    transfer_station(from_s=STATIONS[StationType.DUMMY_1], to_s=STATIONS[StationType.DUMMY_3], delay_s=3)
    transfer_station(from_s=STATIONS[StationType.DUMMY_2], to_s=STATIONS[StationType.DUMMY_3], delay_s=2)

    # s3 full
    if len(STATIONS[StationType.DUMMY_3].available_output) > 0:
        time.sleep(3)
        content_removed = STATIONS[StationType.DUMMY_3].remove_output(STATIONS[StationType.DUMMY_3].available_output[0])
        generated.append(content_removed)

    # epoch
    print(sum(x.qty for x in generated))
    time.sleep(.5)


