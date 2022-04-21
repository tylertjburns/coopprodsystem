from cooptools.coopEnum import CoopEnum
from enum import auto

class StationStatus(CoopEnum):
    IDLE = auto()
    STARVED = auto()
    FULL = auto()
    PRODUCING = auto()
