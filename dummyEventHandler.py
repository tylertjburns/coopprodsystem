import logging

from coopprodsystem import events as cevents
from coopprodsystem.events import OnProductionStartedAtStationEventArgs, OnProductionFinishedAtStationEventArgs
from coopprodsystem.events.absProductionEventHandler import AbsProductionEventHandler

logger = logging.getLogger('dummyeventhandler')


class DummyEventHandler(AbsProductionEventHandler):
    def __init__(self):
        super().__init__()

    def on_production_finished_at_station(self, args: OnProductionFinishedAtStationEventArgs):
        logger.info(f"Production finished at station: {args.station}")

    def on_production_started_at_station(self, args: OnProductionStartedAtStationEventArgs):
        logger.info(f"Production started at station: {args.station}")

    def on_station_added(self, args: cevents.OnStationAddedEventArgs):
        logger.info(f"Station added: {args.station}")

    def on_station_removed(self, args: cevents.OnStationRemovedEventArgs):
        logger.info(f"Station Removed: {args.station}")