from coopprodsystem.my_dataclasses import Content, content_factory, Resource, UoM, UoMType
from dataclasses import dataclass
from functools import partial


@dataclass
class StationResourceDefinition:
    content: Content
    storage_capacity: int

def stationResourceDefinition_factory(station_resource_definition: StationResourceDefinition = None,
                                      content: Content = None,
                                      storage_capacity: int = None,
                                      content_resource: Resource = None,
                                      content_uom: UoM = None,
                                      content_qty: int = None) -> StationResourceDefinition:



    content = content_factory(content=content or (station_resource_definition.content if station_resource_definition else None),
                              resource=content_resource,
                              uom=content_uom,
                              qty=content_qty)

    return StationResourceDefinition(
        content=content,
        storage_capacity=storage_capacity or station_resource_definition.storage_capacity
    )

station_resource_def_EA_uom = partial(stationResourceDefinition_factory, content_uom=UoM(UoMType.EACH))