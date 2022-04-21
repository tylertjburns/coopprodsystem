from dataclasses import dataclass, field
from coopprodsystem.factory import Station
from coopprodsystem.my_dataclasses import Content
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
