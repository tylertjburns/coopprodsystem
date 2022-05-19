import coopprodsystem.events as cevents

class NoLocationFoundException(Exception):
    def __init__(self, storage_id: str):
        cevents.raise_event_NoLocationFoundException(cevents.OnNoLocationFoundExceptionEventArgs(
            storage_id=storage_id
        ))
        super().__init__()

class NoLocationWithCapacityException(Exception):
    def __init__(self, storage_id: str):
        cevents.raise_event_NoLocationWithCapacityException(cevents.OnNoLocationWithCapacityExceptionEventArgs(
            storage_id=storage_id
        ))
        super().__init__()

class ContentDoesntMatchLocationException(Exception):
    def __init__(self, storage_id: str):
        cevents.raise_event_ContentDoesntMatchLocationException(cevents.OnContentDoesntMatchLocationExceptionEventArgs(
            storage_id=storage_id
        ))
        super().__init__()

class ContentDoesntMatchLocationDesignationException(Exception):
    def __init__(self, storage_id: str):
        cevents.raise_event_ContentDoesntMatchLocationDesignationException(cevents.OnContentDoesntMatchLocationDesignationExceptionEventArgs(
            storage_id=storage_id
        ))
        super().__init__()

class NoRoomAtLocationException(Exception):
    def __init__(self, storage_id: str):
        cevents.raise_event_NoRoomAtLocationException(cevents.OnNoRoomAtLocationExceptionEventArgs(
            storage_id=storage_id
        ))
        super().__init__()

class MissingContentException(Exception):
    def __init__(self, storage_id: str):
        cevents.raise_event_MissingContentException(cevents.OnMissingContentExceptionEventArgs(
            storage_id=storage_id
        ))
        super().__init__()

class NoLocationToRemoveContentException(Exception):
    def __init__(self, storage_id: str):
        cevents.raise_event_NoLocationToRemoveContentException(cevents.OnNoLocationToRemoveContentExceptionEventArgs(
            storage_id=storage_id
        ))
        super().__init__()
