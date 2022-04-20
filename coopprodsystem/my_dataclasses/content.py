import uuid
from dataclasses import dataclass, field
from coopprodsystem.my_dataclasses.resource import Resource, ResourceType
from coopprodsystem.my_dataclasses.unitOfMeasure import UoM

class ContentFactoryException(Exception):
    def __init__(self):
        super().__init__(str(type(self)))

@dataclass(frozen=True)
class Content:
    resource: Resource
    uom: UoM
    qty: float
    id: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'id', uuid.uuid4())

    def match_resouce_uom(self, content):
        return content.resource == self.resource and content.uom == self.uom


def content_factory(content: Content = None,
                    resource: Resource = None,
                    resource_name: str = None,
                    resource_description: str = None,
                    resource_type: ResourceType = None,
                    uom: UoM = None,
                    qty: float = None
                    ) -> Content:



    # try to create a resource
    if resource is None and all([resource_name, resource_type, resource_description]):
        resource = Resource(name=resource_name,
                            description=resource_description,
                            type=resource_type)

    # verify all values
    if not content and not all([resource, uom, qty]):
        raise ContentFactoryException()

    # create and return
    return Content(
        resource=resource or content.resource,
        uom=uom or content.uom,
        qty=qty or content.qty
    )


