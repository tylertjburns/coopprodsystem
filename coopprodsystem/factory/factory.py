from coopprodsystem.my_dataclasses import Content, Resource, UoM
from typing import Dict

class Factory:

    def __init__(self):
        self._prod_lines: Dict[str, ProdLine] = {}

