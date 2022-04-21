import logging

from pubsub import pub
from enum import Enum, auto
import datetime
from dataclasses import dataclass, field
from typing import Optional

class ProductionEventType(Enum):
    STATION_ADDED = auto()
    STATION_REMOVED = auto()
    PRODUCTION_FINISHED_AT_STATION = auto()
    PRODUCTION_STARTED_AT_STATION = auto()


@dataclass(frozen=True)
class EventArgsBase:
    date_stamp: Optional[datetime.datetime] = field(init=False)

    def __post_init__(self):
        if self.date_stamp is None:
            object.__setattr__(self, 'date_stamp', datetime.datetime.now())

@dataclass(frozen=True)
class StationEventArgsBase(EventArgsBase):
    station_id: str

@dataclass(frozen=True)
class OnStationAddedEventArgs(StationEventArgsBase):
    ...

@dataclass(frozen=True)
class OnStationRemovedEventArgs(StationEventArgsBase):
    ...

@dataclass(frozen=True)
class OnProductionFinishedAtStationEventArgs(StationEventArgsBase):
    ...

@dataclass(frozen=True)
class OnProductionStartedAtStationEventArgs(StationEventArgsBase):
    ...


def raise_event(event: ProductionEventType, **kwargs):
    logging.debug(f"raise event: {event}")
    pub.sendMessage(event.name, **kwargs)


def raise_station_removed(args: OnStationRemovedEventArgs):
    raise_event(ProductionEventType.STATION_REMOVED, args=args)

def raise_station_added(args: OnStationAddedEventArgs):
    raise_event(ProductionEventType.STATION_ADDED, args=args)

def raise_event_production_finished_at_station(args: OnProductionFinishedAtStationEventArgs):
    raise_event(ProductionEventType.PRODUCTION_FINISHED_AT_STATION, args=args)


def raise_event_production_started_at_station(args: OnProductionStartedAtStationEventArgs):
    raise_event(ProductionEventType.PRODUCTION_STARTED_AT_STATION, args=args)


if __name__ == "__main__":
    pass