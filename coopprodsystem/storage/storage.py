import uuid
from coopprodsystem.my_dataclasses import Location, Content, content_factory, UoM, UoMType, Resource, ResourceUoM
from typing import List, Dict, Optional
import threading
from coopprodsystem.storage.exceptions import *

class Storage:

    def __init__(self,
                 locations: List[Location],
                 id: str = None):

        self._id = id or uuid.uuid4()
        self._inventory: Dict[Location, List[Content]] = {location: [] for location in locations}
        self._loc_designated_uom_types: Dict[Location, Optional[UoMType]] = {location: None for location in locations}
        self._active_uom_type_designations: Dict[Location, Optional[UoMType]] = {location: None for location in locations}
        self._lock = threading.RLock()

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
            raise NoLocationFoundException(storage=self)

        # locations with capacity
        space_at_matches = self.space_at_locations(uom=content.uom, locations=matches)
        matches = [loc for loc in matches if space_at_matches[loc] >= content.qty]

        if len(matches) == 0:
            raise NoLocationWithCapacityException(storage=self,
                                                  content=content,
                                                  resource_uom_space=self.space_for_resource_uom(
                                                      resource_uoms=[content.resourceUoM])[content.resourceUoM],
                                                  loc_uom_space_avail=self.space_at_locations(uom=content.uom),
                                                  loc_uom_designations=self._active_uom_type_designations
                                                  )

        return next(iter(matches))

    def _merge_content(self, content_list: List[Content]) -> List[Content]:
        content_by_ru = {}
        for content in content_list:
            content_by_ru.setdefault(content.resourceUoM, [])
            content_by_ru[content.resourceUoM].append(content)

        ret = []
        for ru, c_list in content_by_ru.items():
            ret.append(content_factory(c_list[0], qty=sum(x.qty for x in c_list)))

        return ret

    def _add_content_to_loc(self, location: Location, content: Content):
        with self._lock:
            # verify content matches uom capacity
            if content.uom.type not in location.uom_capacities:
                raise ContentDoesntMatchLocationException(storage=self)

            # verify the uom matches loc designated uom
            designated_uom_type = self._active_uom_type_designations[location]
            if designated_uom_type and content.uom.type != self._active_uom_type_designations[location]:
                raise ContentDoesntMatchLocationDesignationException(storage=self)

            # verify capacity
            qty_at_loc = self.qty_resource_uom_at_location(location, content.resourceUoM)
            if qty_at_loc + content.qty > location.uom_capacities[content.uom.type]:
                raise NoRoomAtLocationException(storage=self)

            # add content and merge at location
            self._inventory[location].append(content)
            self._inventory[location] = self._merge_content(self._inventory[location])
            self._active_uom_type_designations[location] = content.uom.type

    def _remove_content_from_location(self, content: Content, location: Location) -> Content:
        if content not in self._inventory[location]:
            raise MissingContentException(storage=self)

        idx_of_content = self._inventory[location].index(content)
        removed = self._inventory[location].pop(idx_of_content)

        return removed

    def remove_content(
            self,
            content: Content,
            location: Location = None) -> Content:
        with self._lock:
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
                raise NoLocationToRemoveContentException(storage=self)

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
            if len(self.content_at_location(location)) == 0 and self._loc_designated_uom_types.get(location, None) is None:
                self._active_uom_type_designations[location] = None

            # roll up
            ret = content_factory(removed_cnt[0], qty=sum(x.qty for x in removed_cnt))

            if ret.qty != content.qty:
                raise ValueError(f"The qty returned does not match the qty requested")

        return ret


    def aggregage_content_by_location(self,
                                      location_filter: List[Location] = None,
                                      resource_uom_filter: List[ResourceUoM] = None) -> Dict[Location, List[Content]]:
        if location_filter is None:
            location_filter = self.Locations

        # default the ret to at least include everything in location_filter param
        ret = {loc: [] for loc in location_filter}

        # scan entire inventory
        for loc, content in self._inventory.items():
            # skip locs not in defined range
            if location_filter is not None and loc not in location_filter:
                continue

            # skip resourceUoM if not valid
            for cont in content:
                if resource_uom_filter and cont.resourceUoM not in resource_uom_filter:
                    continue

                # accumulate the found content
                ret[loc].append(cont)
                ret[loc] = self._merge_content(ret[loc])

        return ret



    def content_at_location(self, location: Location, resource_uoms: List[ResourceUoM] = None) -> List[Content]:
        content = self._inventory[location]
        if resource_uoms:
            content = [x for x in content if x.resourceUoM in resource_uoms]

        return content

    def qty_resource_uom_at_location(self, location: Location, resource_uom: ResourceUoM):
        qty = sum([x.qty for x in self.content_at_location(location, resource_uoms=[resource_uom])])
        return qty

    def space_at_locations(self, uom: UoM, locations: List[Location] = None) -> Dict[Location, float]:
        ret = {}

        if locations is None:
            locations = self.Locations

        for location in locations:
            if self._active_uom_type_designations[location] in [None, uom.type]:
                content_at_loc = self.content_at_location(location)
                ret[location] = location.uom_capacities[uom.type] - sum(x.qty for x in content_at_loc)
            else:
                ret[location] = 0

        return ret

    def find_resource_uoms(self,
                           resource_uoms: List[ResourceUoM],
                           location_range: List[Location] = None) -> Dict[Location, List[Content]]:
        return self.aggregage_content_by_location(location_filter=location_range, resource_uom_filter=resource_uoms)

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
                       if self._active_uom_type_designations[loc] in uom_types]

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
        content_by_loc = self.aggregage_content_by_location(location_filter=location_range, resource_uom_filter=resource_uoms)

        # default the ret to at least include everything in resource_uoms param
        ret = {x: 0 for x in resource_uoms} if resource_uoms else {}

        # accumulate the qty of resource uoms
        for loc, c_lst in content_by_loc.items():
            for c in c_lst:
                if resource_uoms and c.resourceUoM not in resource_uoms:
                    continue
                ret.setdefault(c.resourceUoM, 0)
                ret[c.resourceUoM] += c.qty

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
                [space for loc, space in self.space_at_locations(locations=locs, uom=resource_uom.uom).items()])
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
    def Locations(self) -> List[Location]:
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