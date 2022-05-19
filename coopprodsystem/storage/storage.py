import uuid
from coopprodsystem.my_dataclasses import Location, Content, content_factory, UoM, UoMType, Resource, ResourceUoM
from typing import List, Dict, Optional
import threading
from .exceptions import *

class Storage:

    def __init__(self,
                 locations: List[Location],
                 id: str = None):

        self._id = id or uuid.uuid4()
        self._inventory: Dict[Location, List[Content]] = {location: [] for location in locations}
        self._loc_designated_uom_types: Dict[Location, Optional[UoMType]] = {location: None for location in locations}

    def __str__(self):
        return f"id: {self._id}, Locs: {len(self._inventory)}, occupied: {len(self.occupied_locs)}, empty: {len(self.empty_locs)}"

    def print(self):
        print(self._inventory)

    def add_content(self, content: Content, location: Location = None):
        # ensure concrete location
        if location is None:
            location = self.find_open_location(content)

        # try to add content to location
        self._add_content_to_loc(location, content)

    def find_open_location(self, content: Content) -> Location:
        # locs matching required uom and resource limitation
        matches = self.location_match(uom_types=[content.uom.type, None], loc_resource_limits=[content.resource])

        if len(matches) == 0:
            raise NoLocationFoundException(storage_id=self._id)

        # locations with capacity
        matches = [loc for loc in matches if
                   self.qty_resource_uom_at_location(loc, content.resourceUoM) + content.qty <= loc.uom_capacities[
                       content.uom.type]]

        if len(matches) == 0:
            raise NoLocationWithCapacityException(storage_id=self._id)

        return next(iter(matches))

    def _add_content_to_loc(self, location: Location, content: Content):
        # verify content matches uom capacity
        if content.uom.type not in location.uom_capacities:
            raise ContentDoesntMatchLocationException(storage_id=self._id)

        # verify the uom matches loc designated uom
        designated_uom_type = self._loc_designated_uom_types[location]
        if designated_uom_type and content.uom.type != self._loc_designated_uom_types[location]:
            raise ContentDoesntMatchLocationDesignationException(storage_id=self._id)

        # verify capacity
        qty_at_loc = self.qty_resource_uom_at_location(location, content.resourceUoM)
        if qty_at_loc + content.qty > location.uom_capacities[content.uom.type]:
            raise NoRoomAtLocationException(storage_id=self._id)

        # add content at location
        self._inventory[location].append(content)
        self._loc_designated_uom_types[location] = content.uom.type

    def _remove_content_from_location(self, content: Content, location: Location) -> Content:
        if content not in self._inventory[location]:
            raise MissingContentException(storage_id=self._id)

        idx_of_content = self._inventory[location].index(content)
        removed = self._inventory[location].pop(idx_of_content)

        return removed

    def remove_content(
            self,
            content: Content,
            location: Location = None) -> Content:
        if location is None:
            locations_that_satisfy = self.location_match(resource_uoms=[content.resourceUoM], uom_types=[content.uom.type])
            location = next(iter([loc for loc in locations_that_satisfy
                                  if self.qty_resource_uom_at_location(loc, resource_uom=content.resourceUoM) >= content.qty])
                            , None)
        else:
            # TODO: RESOLVE bad location
            raise NotImplementedError()

        # handle no location found
        if location is None:
            raise NoLocationToRemoveContentException(storage_id=self._id)


        with threading.Lock():
            cnt_at_loc = self.content_at_location(location, resource_uoms=[content.resourceUoM])
            removed_cnt = []
            while sum(x.qty for x in removed_cnt) < content.qty:
                cntnt_to_remove = next(x for x in cnt_at_loc if x not in removed_cnt)
                removed = self._remove_content_from_location(cntnt_to_remove, location=location)
                removed_cnt.append(removed)

            # reconcile removed content
            delta = sum(x.qty for x in removed_cnt) - content.qty
            if delta > 0:
                # remove split from location
                to_split = next(x for x in removed_cnt if x.qty >= delta)
                removed_cnt.remove(to_split)

                # decide what to keep out and what to put back
                if to_split.qty == delta:
                    to_put_back_cntnt = to_split
                else:

                    to_keep_cntnt = content_factory(to_split, qty=to_split.qty - delta)
                    removed_cnt.append(to_keep_cntnt)
                    to_put_back_cntnt = content_factory(to_split, qty=delta)

                # put back content
                self._add_content_to_loc(content=to_put_back_cntnt, location=location)

        # If empty, clear location uom designation
        if len(self.content_at_location(location)) == 0:
            self._loc_designated_uom_types[location] = None

        # roll up
        ret = content_factory(removed_cnt[0], qty=sum(x.qty for x in removed_cnt))

        if ret.qty != content.qty:
            raise ValueError(f"The qty returned does not match the qty requested")

        return ret


    def content_at_location(self, location: Location, resource_uoms: List[ResourceUoM] = None) -> List[Content]:
        content = self._inventory[location]
        if resource_uoms:
            content = [x for x in content if x.resourceUoM in resource_uoms]

        return content

    def qty_resource_uom_at_location(self, location: Location, resource_uom: ResourceUoM):
        qty = sum([x.qty for x in self.content_at_location(location, resource_uoms=[resource_uom])])
        return qty

    def space_at_location(self, locations: List[Location], uom: UoM) -> Dict[Location, float]:
        ret = {}
        for location in locations:
            if self._loc_designated_uom_types[location] in [None, uom.type]:
                content_at_loc = self.content_at_location(location)
                ret[location] = location.uom_capacities[uom.type] - sum(x.qty for x in content_at_loc)
            else:
                ret[location] = 0

        return ret

    def find_resource_uoms(self,
                           resource_uoms: List[ResourceUoM],
                           location_range: List[Location] = None) -> Dict[Location, List[Content]]:
        matches = self.location_match(resource_uoms=resource_uoms,
                                      location_range=location_range)
        return {loc: [cont for cont in content if cont.resourceUoM in resource_uoms] for loc, content in
                self._inventory.items()
                if loc in matches}

    def location_match(self,
                       resource_uoms: List[ResourceUoM] = None,
                       uom_types: List[UoMType] = None,
                       loc_resource_limits: List[Resource] = None,
                       location_range: List[Location] = None) -> List[Location]:
        matches = [loc for loc in self._inventory.keys()]

        if location_range:
            matches = [loc for loc in matches if loc in location_range]

        if uom_types:
            matches = [loc for loc in matches
                       if self._loc_designated_uom_types[loc] in uom_types]

        if resource_uoms:
            matches = [loc for loc in matches
                       if any(c.resourceUoM in resource_uoms for c in self._inventory[loc])]

        if loc_resource_limits:
            matches = [loc for loc in matches
                       if not loc.resource_limitations or all(x in loc.resource_limitations
                                                           for x in loc_resource_limits)]

        return matches

    def qty_of_resource_uoms(self,
                             resource_uoms: List[ResourceUoM] = None,
                             location_range: List[Location] = None) -> Dict[ResourceUoM, float]:

        # default the ret to at least include everything in resource_uoms param
        ret = {x: 0 for x in resource_uoms} if resource_uoms else {}

        # scan entire inventory
        for loc, content in self._inventory.items():
            # skip locs not in defined range
            if location_range is not None and loc not in location_range:
                continue

            for cont in content:
                # skip resourceUoM if not valid
                if resource_uoms and cont.resourceUoM not in resource_uoms:
                    continue

                # accumulate the found content
                ret.setdefault(cont.resourceUoM, 0)
                ret[cont.resourceUoM] += cont.qty
        return ret

    def space_for_resource_uom(self,
                               resource_uoms: List[ResourceUoM],
                               only_designated: bool = True) -> Dict[ResourceUoM, float]:
        if not only_designated:
            raise NotImplementedError()

        ret = {}
        for resource_uom in resource_uoms:
            locs = self.location_match(loc_resource_limits=[resource_uom.resource])
            available_space = sum(
                [space for loc, space in self.space_at_location(locations=locs, uom=resource_uom.uom).items()])
            ret[resource_uom] = available_space
        return ret

    @property
    def occupied_locs(self):
        return [loc for loc, cont in self._inventory.items() if len(cont) > 0]

    @property
    def empty_locs(self):
        return [loc for loc, cont in self._inventory.items() if len(cont) == 0]

    @property
    def inventory_by_resource_uom(self) -> Dict[ResourceUoM, float]:
        return self.qty_of_resource_uoms()

    @property
    def rolled_inventory(self) -> List[Content]:
        print(f"usage of property will be depricated. Please make necessary changes to use inventory_by_resource_uom instead")

        inv_by_resource = self.inventory_by_resource_uom

        ret = []
        for resource_uom, qty in inv_by_resource.items():
            ret.append(Content(resourceUoM=resource_uom, qty=qty))
        return ret

    @property
    def locations(self) -> List[Location]:
        return list(self._inventory.keys())

if __name__ == "__main__":
    from coopprodsystem.my_dataclasses import Resource, ResourceType, UoM
    import pprint

    uom_type_capacities = {UoMType.EACH: 10}
    locs = [Location(uom_type_capacities, id=str(ii)) for ii in range(10)]

    inv = Storage(locs)

    sku_a = Resource('a', 'a desc', ResourceType.DEFAULT)
    ru_a = ResourceUoM(sku_a, UoM(UoMType.EACH))
    for ii in range(4):
        content = Content(
            resourceUoM=ru_a,
            qty=3
        )
        inv.add_content(content)

    print(inv)
    pprint.pprint(inv.find_resource_uoms([ru_a]))

    inv.remove_content(Content(ResourceUoM(sku_a, UoM(UoMType.EACH)), 9))

    print(inv.inventory_by_resource_uom)