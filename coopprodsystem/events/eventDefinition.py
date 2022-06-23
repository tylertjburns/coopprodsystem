import logging

from pubsub import pub
from enum import Enum, auto
import datetime
from dataclasses import dataclass, field
from coopprodsystem.factory.stationTransfer import StationTransfer
from coopprodsystem.factory.station import Station

logger = logging.getLogger('coopprodsystem.events')

class ProductionEventType(Enum):
    STATION_ADDED = auto()
    STATION_REMOVED = auto()
    PRODUCTION_FINISHED_AT_STATION = auto()
    PRODUCTION_STARTED_AT_STATION = auto()
    STATION_TRANSFER_STARTED = auto()
    STATION_TRANSFER_COMPLETED = auto()

#region EventArgsBase
@dataclass(frozen=True)
class EventArgsBase:
    date_stamp: datetime.datetime = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'date_stamp', datetime.datetime.now())

@dataclass(frozen=True)
class StationEventArgsBase(EventArgsBase):
    station: Station

@dataclass(frozen=True)
class StationTransferEventArgsBase(EventArgsBase):
    transfer: StationTransfer
#endregion

#region EventArgs
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

@dataclass(frozen=True)
class OnStationTransferStartedEventArgs(StationTransferEventArgsBase):
    ...

@dataclass(frozen=True)
class OnStationTransferCompletedEventArgs(StationTransferEventArgsBase):
    ...

#endregion

#region RaiseEvents
def raise_event(event: ProductionEventType,
                log_lvl = logging.INFO, 
                **kwargs):
    args = kwargs.get('args', None)
    logger.log(level=log_lvl, msg=f"raise event: {event.name} with args: {args}")
    pub.sendMessage(event.name, **kwargs)


def raise_station_removed(args: OnStationRemovedEventArgs):
    raise_event(ProductionEventType.STATION_REMOVED, log_lvl=logging.INFO, args=args)

def raise_station_added(args: OnStationAddedEventArgs):
    raise_event(ProductionEventType.STATION_ADDED, log_lvl=logging.INFO, args=args)

def raise_event_production_finished_at_station(args: OnProductionFinishedAtStationEventArgs):
    raise_event(ProductionEventType.PRODUCTION_FINISHED_AT_STATION, log_lvl=logging.INFO, args=args)

def raise_event_production_started_at_station(args: OnProductionStartedAtStationEventArgs):
    raise_event(ProductionEventType.PRODUCTION_STARTED_AT_STATION, log_lvl=logging.INFO, args=args)

def raise_event_StationTransferStarted(args: OnStationTransferStartedEventArgs):
    raise_event(ProductionEventType.STATION_TRANSFER_STARTED, log_lvl=logging.INFO, args=args)

def raise_event_StationTransferCompleted(args: OnStationTransferCompletedEventArgs):
    raise_event(ProductionEventType.STATION_TRANSFER_COMPLETED, log_lvl=logging.INFO, args=args)
#endregion

if __name__ == "__main__":
    pass