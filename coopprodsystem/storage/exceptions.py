import coopprodsystem.events as cevents

class NoLocationFoundException(Exception):
    def __init__(self, storage):
        cevents.raise_event_NoLocationFoundException(cevents.OnNoLocationFoundExceptionEventArgs(
            storage=storage
        ))
        super().__init__()

class NoLocationWithCapacityException(Exception):
    def __init__(self, storage, content, resource_uom_space, loc_uom_space_avail, loc_uom_designations):
        cevents.raise_event_NoLocationWithCapacityException(cevents.OnNoLocationWithCapacityExceptionEventArgs(
            storage=storage,
            content=content,
            resource_uom_space=resource_uom_space,
            loc_uom_space_avail=loc_uom_space_avail,
            loc_uom_designations=loc_uom_designations
        ))
        super().__init__()

class ContentDoesntMatchLocationException(Exception):
    def __init__(self, storage):
        cevents.raise_event_ContentDoesntMatchLocationException(cevents.OnContentDoesntMatchLocationExceptionEventArgs(
            storage=storage
        ))
        super().__init__()

class ContentDoesntMatchLocationDesignationException(Exception):
    def __init__(self, storage):
        cevents.raise_event_ContentDoesntMatchLocationDesignationException(cevents.OnContentDoesntMatchLocationDesignationExceptionEventArgs(
            storage=storage
        ))
        super().__init__()

class NoRoomAtLocationException(Exception):
    def __init__(self, storage):
        cevents.raise_event_NoRoomAtLocationException(cevents.OnNoRoomAtLocationExceptionEventArgs(
            storage=storage
        ))
        super().__init__()

class MissingContentException(Exception):
    def __init__(self, storage):
        cevents.raise_event_MissingContentException(cevents.OnMissingContentExceptionEventArgs(
            storage=storage
        ))
        super().__init__()

class NoLocationToRemoveContentException(Exception):
    def __init__(self, storage):
        cevents.raise_event_NoLocationToRemoveContentException(cevents.OnNoLocationToRemoveContentExceptionEventArgs(
            storage=storage
        ))
        super().__init__()
