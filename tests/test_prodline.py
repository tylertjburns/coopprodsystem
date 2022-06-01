import unittest
from coopprodsystem import ProductionLine, Station
from station_manifest import STATIONS
from coopstructs.vectors import Vector2
import random as rnd

class Test_ProdLine(unittest.TestCase):

    def test__init_empty_prod_line(self):
        # arrange

        # act
        pl = ProductionLine(
            init_stations=[],
            start_on_init=True
        )

        # assert
        self.assertEqual(len(pl.Stations), 0)


    def test__init__prod_line(self):
        # arrange
        stations = [(x, Vector2(rnd.randint(0, 10), rnd.randint(0, 10))) for x in STATIONS.values()]
        # act
        pl = ProductionLine(
            init_stations=stations,
            start_on_init=True
        )

        # assert
        self.assertEqual(len(pl.Stations), len(stations))