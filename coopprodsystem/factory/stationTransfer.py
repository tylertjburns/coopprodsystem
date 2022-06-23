from dataclasses import dataclass, field
from coopprodsystem.factory.station import Station
from coopstorage.my_dataclasses import Content
from cooptools.timedDecay import Timer
import uuid

@dataclass(frozen=True)
class StationTransfer:
    from_station: Station
    to_station: Station
    content: Content
    timer: Timer
    id: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'id', uuid.uuid4())

    def __hash__(self):
        return hash(self.id)


    def short_str(self):
        from_station_txt = f"{self.from_station.id[:7]}..." if len(self.from_station.id) > 10 else self.from_station.id
        to_station_txt = f"{self.to_station.id[:7]}..." if len(self.to_station.id) > 10 else self.to_station.id
        return f"{from_station_txt}->{to_station_txt}: {self.content.resourceUoM.resource.name}/{self.content.resourceUoM.uom.name} {self.content.qty}"

