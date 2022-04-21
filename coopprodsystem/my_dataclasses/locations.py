from dataclasses import dataclass
from coopprodsystem.my_dataclasses import UoMType, Resource
from typing import Dict, Optional, List
import uuid

@dataclass(frozen=True)
class Location:
    uom_capacities: Dict[UoMType, int]
    resource_limitations: List[Resource] = None
    id: Optional[str] = None

    def __post_init__(self):
        if self.id is None: object.__setattr__(self, 'id', uuid.uuid4())

    def __hash__(self):
        return hash(self.id)