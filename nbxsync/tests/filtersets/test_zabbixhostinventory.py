from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.filtersets import ZabbixHostInventoryFilterSet
from nbxsync.models import ZabbixHostInventory


class ZabbixHostInventoryFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.devices = [
            create_test_device(name='HostInventory Test Device 1'),
            create_test_device(name='HostInventory Test Device 2'),
            create_test_device(name='HostInventory Test Device 3'),
            create_test_device(name='HostInventory Test Device 4'),
        ]

        cls.device_ct = ContentType.objects.get_for_model(Device)

        cls.inventoryassignments = [
            ZabbixHostInventory.objects.create(
                alias='WebServer01',
                tag='web',
                vendor='Dell',
                location='Datacenter A',
                os='Ubuntu',
                software='Apache',
                inventory_mode=0,
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[0].id,
            ),
            ZabbixHostInventory.objects.create(
                alias='DbServer01',
                tag='db',
                vendor='HP',
                location='Datacenter B',
                os='CentOS',
                software='PostgreSQL',
                inventory_mode=1,
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[1].id,
            ),
        ]

    def test_search_by_alias(self):
        f = ZabbixHostInventoryFilterSet({'q': 'WebServer'}, queryset=ZabbixHostInventory.objects.all())
        self.assertIn(self.inventoryassignments[0], f.qs)
        self.assertNotIn(self.inventoryassignments[1], f.qs)

    def test_search_by_tag(self):
        f = ZabbixHostInventoryFilterSet({'q': 'db'}, queryset=ZabbixHostInventory.objects.all())
        self.assertIn(self.inventoryassignments[1], f.qs)
        self.assertNotIn(self.inventoryassignments[0], f.qs)

    def test_search_by_vendor(self):
        f = ZabbixHostInventoryFilterSet({'q': 'Dell'}, queryset=ZabbixHostInventory.objects.all())
        self.assertIn(self.inventoryassignments[0], f.qs)

    def test_search_by_os(self):
        f = ZabbixHostInventoryFilterSet({'q': 'Ubuntu'}, queryset=ZabbixHostInventory.objects.all())
        self.assertIn(self.inventoryassignments[0], f.qs)

    def test_search_by_software(self):
        f = ZabbixHostInventoryFilterSet({'q': 'PostgreSQL'}, queryset=ZabbixHostInventory.objects.all())
        self.assertIn(self.inventoryassignments[1], f.qs)

    def test_search_with_blank_value_returns_all(self):
        queryset = ZabbixHostInventory.objects.all()
        f = ZabbixHostInventoryFilterSet({'q': ''}, queryset=queryset)
        self.assertQuerySetEqual(f.qs.order_by('pk'), queryset.order_by('pk'), transform=lambda x: x)

    def test_search_method_directly_hits_return_queryset(self):
        queryset = ZabbixHostInventory.objects.all()
        f = ZabbixHostInventoryFilterSet({}, queryset=queryset)
        result = f.search(queryset, name='q', value='   ')
        self.assertQuerySetEqual(result.order_by('pk'), queryset.order_by('pk'), transform=lambda x: x)

    def test_filter_by_inventory_mode(self):
        f = ZabbixHostInventoryFilterSet({'inventory_mode': 1}, queryset=ZabbixHostInventory.objects.all())
        self.assertIn(self.inventoryassignments[1], f.qs)
        self.assertNotIn(self.inventoryassignments[0], f.qs)

    def test_filter_by_alias_field(self):
        f = ZabbixHostInventoryFilterSet({'alias': 'WebServer'}, queryset=ZabbixHostInventory.objects.all())
        self.assertIn(self.inventoryassignments[0], f.qs)

    def test_filter_by_tag_field(self):
        f = ZabbixHostInventoryFilterSet({'tag': 'web'}, queryset=ZabbixHostInventory.objects.all())
        self.assertIn(self.inventoryassignments[0], f.qs)

    def test_filter_by_vendor_field(self):
        f = ZabbixHostInventoryFilterSet({'vendor': 'HP'}, queryset=ZabbixHostInventory.objects.all())
        self.assertIn(self.inventoryassignments[1], f.qs)

    def test_filter_by_assigned_object_type(self):
        f = ZabbixHostInventoryFilterSet({'assigned_object_type': f'{self.device_ct.app_label}.{self.device_ct.model}'}, queryset=ZabbixHostInventory.objects.all())
        self.assertEqual(f.qs.count(), 2)

    def test_filter_fails_with_wrong_content_type(self):
        wrong_ct = ContentType.objects.get_for_model(ZabbixHostInventory)
        f = ZabbixHostInventoryFilterSet(
            {'assigned_object_type': f'{wrong_ct.app_label}.{wrong_ct.model}', 'assigned_object_id': self.devices[0].id},
            queryset=ZabbixHostInventory.objects.all(),
        )
        self.assertEqual(f.qs.count(), 0)

    def test_filter_by_assigned_object_id_alone(self):
        f = ZabbixHostInventoryFilterSet({'assigned_object_id': self.devices[0].id}, queryset=ZabbixHostInventory.objects.all())
        self.assertIn(self.inventoryassignments[0], f.qs)
        self.assertNotIn(self.inventoryassignments[1], f.qs)
