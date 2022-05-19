import unittest
from coopprodsystem.storage.storage import Storage
from coopprodsystem.my_dataclasses import Resource, ResourceType, UoM, Location, UoMType, ResourceUoM, Content

class Test_Storage(unittest.TestCase):

    def test__init_storage(self):
        # arrange
        uom_type_capacities = {UoMType.EACH: 10}
        locs = [Location(uom_type_capacities, id=str(ii)) for ii in range(10)]

        # act
        inv = Storage(locs)

        # assert
        self.assertEqual(len(inv.locations), len(locs))

    def test__storage__add_content(self):
        # arrange
        uom_type_capacities = {UoMType.EACH: 10}
        locs = [Location(uom_type_capacities, id=str(ii)) for ii in range(10)]

        inv = Storage(locs)

        sku_a = Resource('a', 'a desc', ResourceType.DEFAULT)
        ru_a = ResourceUoM(sku_a, UoM(UoMType.EACH))
        n_content = 4
        qty = 3

        # act
        for ii in range(4):
            content = Content(
                resourceUoM=ru_a,
                qty=qty
            )
            inv.add_content(content)

        # assert
        self.assertEqual(inv.inventory_by_resource_uom[ru_a], n_content * qty)
        self.assertEqual(inv.qty_of_resource_uoms(resource_uoms=[ru_a])[ru_a], n_content * qty)
        self.assertEqual(inv.qty_of_resource_uoms()[ru_a], n_content * qty)

    def test__storage__remove_content(self):
        # arrange
        uom_type_capacities = {UoMType.EACH: 10}
        locs = [Location(uom_type_capacities, id=str(ii)) for ii in range(10)]
        inv = Storage(locs)

        sku_a = Resource('a', 'a desc', ResourceType.DEFAULT)
        ru_a = ResourceUoM(sku_a, UoM(UoMType.EACH))
        n_content = 4
        qty = 3
        qty_to_remove = 7

        for ii in range(4):
            content = Content(
                resourceUoM=ru_a,
                qty=qty
            )
            inv.add_content(content)

        # act
        rmvd = inv.remove_content(Content(resourceUoM=ru_a, qty=qty_to_remove))

        # assert
        self.assertEqual(inv.inventory_by_resource_uom[ru_a], n_content * qty - qty_to_remove)
        self.assertEqual(inv.qty_of_resource_uoms(resource_uoms=[ru_a])[ru_a], n_content * qty - qty_to_remove)
        self.assertEqual(inv.qty_of_resource_uoms()[ru_a], n_content * qty - qty_to_remove)
        self.assertEqual(rmvd.qty, qty_to_remove)

