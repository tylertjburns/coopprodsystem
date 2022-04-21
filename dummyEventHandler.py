import logging

from coopprodsystem.events import OnProductionStartedAtStationEventArgs, OnProductionFinishedAtStationEventArgs
from coopprodsystem.events.absProductionEventHandler import AbsProductionEventHandler

logger = logging.getLogger('dummyeventhandler')
class DummyEventHandler(AbsProductionEventHandler):
    def __init__(self):
        super().__init__()

    def on_production_finished_at_station(self, args: OnProductionFinishedAtStationEventArgs):
        logger.info(f"Production finished at station: {args.station_id}")

    def on_production_started_at_station(self, args: OnProductionStartedAtStationEventArgs):
        logger.info(f"Production started at station: {args.station_id}")