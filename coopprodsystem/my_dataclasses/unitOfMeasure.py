from dataclasses import dataclass
from cooptools.coopEnum import CoopEnum
from enum import auto

class UoMType(CoopEnum):
    EACH = auto()
    PALLET = auto()
    BOTTLE = auto()

@dataclass(frozen=True)
class UoM:
    type: UoMType