from dataclasses import dataclass
from coopprodsystem.my_dataclasses import Resource, UoM

@dataclass(frozen=True)
class ResourceUoM:
    resource: Resource
    uom: UoM