from dataclasses import dataclass
from coopprodsystem.my_dataclasses import UoMType, Resource
from typing import Dict, Optional, List

@dataclass(frozen=True)
class Location:
    uom_capacities: Dict[UoMType, int]
    resource_limitations: List[Resource] = None
    id: Optional[str] = None

    def __hash__(self):
        return hash(self.id)