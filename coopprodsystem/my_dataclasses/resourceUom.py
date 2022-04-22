from dataclasses import dataclass
from coopprodsystem.my_dataclasses import Resource, UoM

@dataclass(frozen=True)
class ResourceUoM:
    resource: Resource
    uom: UoM

def resourceUom_factory(resource_uom: ResourceUoM = None,
                        resource: Resource = None,
                        uom: UoM = None) -> ResourceUoM:
    return ResourceUoM(
        resource=resource or resource_uom.resource,
        uom=uom or resource_uom.uom
    )