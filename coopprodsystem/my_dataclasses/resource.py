from dataclasses import dataclass
from cooptools.coopEnum import CoopEnum
from enum import auto

class ResourceType(CoopEnum):
    DEFAULT = auto()

@dataclass(frozen=True)
class Resource:
    name: str
    description: str
    type: ResourceType

def resource_factory(resource: Resource,
                     name: str = None,
                     description: str = None,
                     type: ResourceType = None) -> Resource:
    return Resource(
        name=name or resource.name,
        description=description or resource.description,
        type=type or resource.type
    )

