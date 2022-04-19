import logging

from pubsub import pub
from enum import Enum, auto
import datetime
from dataclasses import dataclass


class ProductionEventType(Enum):
    PRODUCTION_FINISHED_AT_STATION = auto()
    PRODUCTION_STARTED_AT_STATION = auto()


@dataclass(frozen=True)
class EventArgsBase:
    date_stamp: datetime.datetime
    run_time: float


@dataclass(frozen=True)
class OnProductionFinishedAtStationEventArgs(EventArgsBase):
    station_id: str


@dataclass(frozen=True)
class OnProductionStartedAtStationEventArgs(EventArgsBase):
    station_id: str


def raise_event(event: ProductionEventType, **kwargs):
    logging.debug(f"raise event: {event}")
    pub.sendMessage(event.name, **kwargs)


def raise_event_production_finished_at_station(args: OnProductionFinishedAtStationEventArgs):
    raise_event(ProductionEventType.PRODUCTION_FINISHED_AT_STATION, args=args)


def raise_event_production_started_at_station(args: OnProductionStartedAtStationEventArgs):
    raise_event(ProductionEventType.PRODUCTION_STARTED_AT_STATION, args=args)


if __name__ == "__main__":
    pass