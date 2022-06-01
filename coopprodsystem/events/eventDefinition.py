import logging

from pubsub import pub
from enum import Enum, auto
import datetime
from dataclasses import dataclass, field
from coopprodsystem.factory.stationTransfer import StationTransfer
from coopprodsystem.factory.station import Station
from coopprodsystem.storage import Storage

logger = logging.getLogger('coopprodsystem.events')

class ProductionEventType(Enum):
    STATION_ADDED = auto()
    STATION_REMOVED = auto()
    PRODUCTION_FINISHED_AT_STATION = auto()
    PRODUCTION_STARTED_AT_STATION = auto()
    STATION_TRANSFER_STARTED = auto()
    STATION_TRANSFER_COMPLETED = auto()
    EXCEPTION_NO_LOCATION_FOUND = auto()
    EXCEPTION_NO_LOCATION_WITH_CAPACITY_FOUND = auto()
    EXCEPTION_CONTENT_DOESNT_MATCH_LOCATION = auto()
    EXCEPTION_CONTENT_DOESNT_MATCH_LOCATION_DESIGNATION = auto()
    EXCEPTION_NO_ROOM_AT_LOCATION = auto()
    EXCEPTION_MISSING_CONTENT = auto()
    EXCEPTION_NO_LOCATION_TO_REMOVE_CONTENT = auto()

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
class StorageEventArgsBase(EventArgsBase):
    storage: Storage

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

#region ExceptionEventArgs
@dataclass(frozen=True)
class OnNoLocationFoundExceptionEventArgs(StorageEventArgsBase):
    ...

@dataclass(frozen=True)
class OnNoLocationWithCapacityExceptionEventArgs(StorageEventArgsBase):
    ...

@dataclass(frozen=True)
class OnContentDoesntMatchLocationExceptionEventArgs(StorageEventArgsBase):
    ...

@dataclass(frozen=True)
class OnContentDoesntMatchLocationDesignationExceptionEventArgs(StorageEventArgsBase):
    ...

@dataclass(frozen=True)
class OnNoRoomAtLocationExceptionEventArgs(StorageEventArgsBase):
    ...

@dataclass(frozen=True)
class OnMissingContentExceptionEventArgs(StorageEventArgsBase):
    ...

@dataclass(frozen=True)
class OnNoLocationToRemoveContentExceptionEventArgs(StorageEventArgsBase):
    ...
#endregion

#region RaiseEvents
def raise_event(event: ProductionEventType, log_lvl, **kwargs):
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


def raise_event_NoLocationFoundException(args: OnNoLocationFoundExceptionEventArgs):
    raise_event(ProductionEventType.EXCEPTION_NO_LOCATION_FOUND, log_lvl=logging.ERROR, args=args)

def raise_event_NoLocationWithCapacityException(args: OnNoLocationWithCapacityExceptionEventArgs):
    raise_event(ProductionEventType.EXCEPTION_NO_LOCATION_WITH_CAPACITY_FOUND, log_lvl=logging.ERROR, args=args)

def raise_event_ContentDoesntMatchLocationException(args: OnContentDoesntMatchLocationExceptionEventArgs):
    raise_event(ProductionEventType.EXCEPTION_CONTENT_DOESNT_MATCH_LOCATION, log_lvl=logging.ERROR, args=args)

def raise_event_ContentDoesntMatchLocationDesignationException(args: OnContentDoesntMatchLocationDesignationExceptionEventArgs):
    raise_event(ProductionEventType.EXCEPTION_CONTENT_DOESNT_MATCH_LOCATION_DESIGNATION, log_lvl=logging.ERROR, args=args)

def raise_event_NoRoomAtLocationException(args: OnNoRoomAtLocationExceptionEventArgs):
    raise_event(ProductionEventType.EXCEPTION_NO_ROOM_AT_LOCATION, log_lvl=logging.ERROR, args=args)

def raise_event_MissingContentException(args: OnMissingContentExceptionEventArgs):
    raise_event(ProductionEventType.EXCEPTION_MISSING_CONTENT, log_lvl=logging.ERROR, args=args)

def raise_event_NoLocationToRemoveContentException(args: OnNoLocationToRemoveContentExceptionEventArgs):
    raise_event(ProductionEventType.EXCEPTION_NO_LOCATION_TO_REMOVE_CONTENT, log_lvl=logging.ERROR, args=args)

def raise_event_StationTransferStarted(args: OnStationTransferStartedEventArgs):
    raise_event(ProductionEventType.STATION_TRANSFER_STARTED, log_lvl=logging.INFO, args=args)

def raise_event_StationTransferCompleted(args: OnStationTransferCompletedEventArgs):
    raise_event(ProductionEventType.STATION_TRANSFER_COMPLETED, log_lvl=logging.INFO, args=args)
#endregion

if __name__ == "__main__":
    pass