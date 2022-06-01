# from .exceptions import *
# from .storage import Storage
# from coopprodsystem import Content, Location, content_factory
# import threading

#TODO: these utils need to be reworked so that they return a frozen storage obj.

# def _add_content_to_loc(storage: Storage, location: Location, content: Content):
#     # verify content matches uom capacity
#     if content.uom.type not in location.uom_capacities:
#         raise ContentDoesntMatchLocationException(storage=storage)
#
#     # verify the uom matches loc designated uom
#     designated_uom_type = storage._loc_designated_uom_types[location]
#     if designated_uom_type and content.uom.type != storage._loc_designated_uom_types[location]:
#         raise ContentDoesntMatchLocationDesignationException(storage=storage)
#
#     # verify capacity
#     qty_at_loc = storage.qty_resource_uom_at_location(location, content.resourceUoM)
#     if qty_at_loc + content.qty > location.uom_capacities[content.uom.type]:
#         raise NoRoomAtLocationException(storage=storage)
#
#     # add content at location
#     storage._inventory[location].append(content)
#     storage._loc_designated_uom_types[location] = content.uom.type
#
# def add_content(storage: Storage, content: Content, location: Location = None):
#     # ensure concrete location
#     if location is None:
#         location = storage.find_open_location(content)
#
#     # try to add content to location
#     _add_content_to_loc(storage=storage,
#                         location=location,
#                         content=content)
#
#
# def remove_content(
#         self,
#         content: Content,
#         location: Location = None) -> Content:
#     if location is None:
#         locations_that_satisfy = self.location_match(resource_uoms=[content.resourceUoM], uom_types=[content.uom.type])
#         location = next(iter([loc for loc in locations_that_satisfy
#                               if self.qty_resource_uom_at_location(loc, resource_uom=content.resourceUoM) >= content.qty])
#                         , None)
#     else:
#         # TODO: RESOLVE bad location
#         raise NotImplementedError()
#
#     # handle no location found
#     if location is None:
#         raise NoLocationToRemoveContentException(storage=self)
#
#
#     with threading.Lock():
#         cnt_at_loc = self.content_at_location(location, resource_uoms=[content.resourceUoM])
#         removed_cnt = []
#         while sum(x.qty for x in removed_cnt) < content.qty:
#             cntnt_to_remove = next(x for x in cnt_at_loc if x not in removed_cnt)
#             removed = self._remove_content_from_location(cntnt_to_remove, location=location)
#             removed_cnt.append(removed)
#
#         # reconcile removed content
#         delta = sum(x.qty for x in removed_cnt) - content.qty
#         if delta > 0:
#             # remove split from location
#             to_split = next(x for x in removed_cnt if x.qty >= delta)
#             removed_cnt.remove(to_split)
#
#             # decide what to keep out and what to put back
#             if to_split.qty == delta:
#                 to_put_back_cntnt = to_split
#             else:
#
#                 to_keep_cntnt = content_factory(to_split, qty=to_split.qty - delta)
#                 removed_cnt.append(to_keep_cntnt)
#                 to_put_back_cntnt = content_factory(to_split, qty=delta)
#
#             # put back content
#             self._add_content_to_loc(content=to_put_back_cntnt, location=location)
#
#     # If empty, clear location uom designation
#     if len(self.content_at_location(location)) == 0:
#         self._loc_designated_uom_types[location] = None
#
#     # roll up
#     ret = content_factory(removed_cnt[0], qty=sum(x.qty for x in removed_cnt))
#
#     if ret.qty != content.qty:
#         raise ValueError(f"The qty returned does not match the qty requested")
#
#     return ret
