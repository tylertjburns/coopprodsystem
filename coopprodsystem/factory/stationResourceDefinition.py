from coopstorage.storage.loc_load.dcs import ContainerContent, Resource, UnitOfMeasure
from dataclasses import dataclass
from functools import partial


@dataclass
class StationResourceDefinition:
    content: ContainerContent
    storage_capacity: int

def stationResourceDefinition_factory(station_resource_definition: StationResourceDefinition = None,
                                      content: ContainerContent = None,
                                      storage_capacity: int = None,
                                      content_resource: Resource = None,
                                      content_uom: UnitOfMeasure = None,
                                      content_qty: int = None) -> StationResourceDefinition:

    content = content or ContainerContent(
        resource=content_resource or station_resource_definition.content.resource,
        uom=content_uom or station_resource_definition.content.uom,
        qty=content_qty or station_resource_definition.content.qty,
    )

    return StationResourceDefinition(
        content=content,
        storage_capacity=storage_capacity or station_resource_definition.storage_capacity
    )

station_resource_def_EA_uom = partial(stationResourceDefinition_factory, content_uom=UnitOfMeasure(name='EACH'))
