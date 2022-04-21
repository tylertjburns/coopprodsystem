from abc import ABC, abstractmethod
import coopprodsystem.events as cevents
from pubsub import pub

class AbsProductionEventHandler(ABC):

    def __init__(self):
        self.register_handlers()

    @abstractmethod
    def on_station_added(self, args: cevents.OnStationAddedEventArgs):
        ...

    @abstractmethod
    def on_station_removed(self, args: cevents.OnStationRemovedEventArgs):
        ...

    @abstractmethod
    def on_production_finished_at_station(self, args: cevents.OnProductionFinishedAtStationEventArgs):
        ...

    @abstractmethod
    def on_production_started_at_station(self, args: cevents.OnProductionStartedAtStationEventArgs):
        ...

    def register_handlers(self):
        pub.subscribe(self.on_production_finished_at_station, cevents.ProductionEventType.PRODUCTION_FINISHED_AT_STATION.name)
        pub.subscribe(self.on_production_started_at_station, cevents.ProductionEventType.PRODUCTION_STARTED_AT_STATION.name)
        pub.subscribe(self.on_station_added, cevents.ProductionEventType.STATION_ADDED.name)
        pub.subscribe(self.on_station_removed, cevents.ProductionEventType.STATION_REMOVED.name)