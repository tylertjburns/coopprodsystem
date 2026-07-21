import time
import unittest
from coopprodsystem import Station, station_factory
from coopprodsystem.factory.stationResourceDefinition import StationResourceDefinition
from coopprodsystem.factory.stationStatus import StationStatus
from coopstorage.storage.loc_load.dcs import ContainerContent
from cooptools.expertise.expertiseSchedules import ByRunsExpertiseSchedule
import sku_manifest as skus
import uom_manifest as uoms
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

    def test__production_cycle__no_inputs__fills_output_to_capacity_and_drains_on_remove(self):
        # arrange -- a raw/gathering station (no input_reqs) that produces 1 unit of raw_1/EACH
        # per run, capped at 5, with a fast timer so the test doesn't need to sleep long.
        key = (skus.raw_1, uoms.each)
        out_def = StationResourceDefinition(
            content=ContainerContent(resource=skus.raw_1, uom=uoms.each, qty=1),
            storage_capacity=5
        )
        station = Station(
            output=[out_def],
            production_timer_sec_callback=lambda: 0.01,
            expertise_schedule=ByRunsExpertiseSchedule(runs_until_expert=3, max_time_reduction_perc=0.5),
            start_on_init=False,
        )

        # act -- tick until output storage is full (bounded to avoid an infinite loop on regression)
        for _ in range(200):
            station.update()
            if station.available_output.get(key, 0.0) >= 5.0:
                break
            time.sleep(0.005)

        # assert -- production ran to capacity and expertise increased along the way
        self.assertEqual(5.0, station.available_output.get(key, 0.0))
        self.assertIn(StationStatus.FULL, station.status)
        self.assertGreater(station.expertise.PercExpert, 0.0)

        # act -- remove everything produced
        removed = station.remove_output(station.available_output_as_content)

        # assert -- storage is drained and the removed content matches what was available
        self.assertEqual(5.0, sum(c.qty for c in removed))
        self.assertEqual({}, station.available_output)
