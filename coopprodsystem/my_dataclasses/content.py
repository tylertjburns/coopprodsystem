import uuid
from dataclasses import dataclass, field
from coopprodsystem.my_dataclasses import Resource, ResourceUoM, ResourceType, UoM, resourceUom_factory, resource_factory

class ContentFactoryException(Exception):
    def __init__(self):
        super().__init__(str(type(self)))

@dataclass(frozen=True)
class Content:
    resourceUoM: ResourceUoM
    qty: float
    id: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'id', uuid.uuid4())
        if self.qty < 0:
            raise ValueError(f"qty cannot be zero, {self.qty} provided")

    def match_resouce_uom(self, content):
        return content.resource == self.resource and content.uom == self.uom

    @property
    def resource(self) -> Resource:
        return self.resourceUoM.resource

    @property
    def uom(self) -> UoM:
        return self.resourceUoM.uom

def content_factory(content: Content = None,
                    resource_uom: ResourceUoM = None,
                    resource: Resource = None,
                    resource_name: str = None,
                    resource_description: str = None,
                    resource_type: ResourceType = None,
                    uom: UoM = None,
                    qty: float = None
                    ) -> Content:

    if all([resource_name, resource_description, resource_type]) or resource:
        resource = resource_factory(resource=resource, description=resource_description, type=resource_type)

    if all([resource, uom]) or resource_uom:
        resource_uom = resourceUom_factory(resource_uom=resource_uom, resource=resource, uom=uom)

    if all([resource_uom, qty]) or content:
        content = Content(
            resourceUoM=resource_uom or content.resourceUoM,
            qty=qty or content.qty
        )

    if content is None:
        raise ContentFactoryException()

    if qty and content.qty != qty:
        deb = True

    return content


    #
    #
    #
    #
    #
    #
    # # try to create a resource
    # if not resource_uom and \
    #         resource is None \
    #         and all([resource_name, resource_type, resource_description]):
    #     resource = Resource(name=resource_name,
    #                         description=resource_description,
    #                         type=resource_type)
    #
    # # verify all values
    # if not content and (resource_uom and qty is not None):
    #     content = Content(resourceUoM=resource_uom, qty=qty)
    # if not content and all([resource, uom, qty]):
    #     content = Content(resourceUoM=ResourceUoM(resource=resource, uom=uom), qty=qty)
    # if content is None:
    #     raise ContentFactoryException()
    #
    # # create and return
    # return Content(
    #     resourceUoM=resource_uom
    # )


