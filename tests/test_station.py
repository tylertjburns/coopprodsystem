import unittest
from coopprodsystem import Station, station_factory
import sku_manifest as skus
import station_manifest as stations

class Test_Station(unittest.TestCase):

    def test__init_station(self):
        # arrange
        name = 'test_dummy'

        # act
        station = station_factory(station_template=stations.s1, id=name)

        # assert
        self.assertEqual(station.input_reqs, stations.s1.input_reqs)
        self.assertEqual(station.outputs, stations.s1.outputs)
        self.assertEqual(len(station.InputStorageState.Locations), len(station.input_reqs))
        self.assertEqual(len(station.OutputStorageState.Locations), len(station.outputs))
        self.assertEqual(station.id, name)
