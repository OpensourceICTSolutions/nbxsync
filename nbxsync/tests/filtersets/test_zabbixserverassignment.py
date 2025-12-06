from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from virtualization.models import VirtualMachine

from dcim.models import Device
from utilities.testing import create_test_device, create_test_virtualmachine

from nbxsync.filtersets import ZabbixServerAssignmentFilterSet
from nbxsync.models import ZabbixServer, ZabbixServerAssignment, ZabbixTag


class ZabbixServerAssignmentFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.queryset = ZabbixServerAssignment.objects.all()
        cls.zabbix_servers = [
            ZabbixServer.objects.create(
                name='Zabbix Server Bulk 1',
                description='Test Bulk Server 1',
                url='http://examplebulk1.com',
                token='bulk1-token',
                validate_certs=True,
            ),
            ZabbixServer.objects.create(
                name='Zabbix Server Bulk 2',
                description='Test Bulk Server 2',
                url='http://examplebulk2.com',
                token='bulk2-token',
                validate_certs=True,
            ),
            ZabbixServer.objects.create(
                name='Zabbix Server Bulk 3',
                description='Test Bulk Server 3',
                url='http://examplebulk3.com',
                token='bulk3-token',
                validate_certs=True,
            ),
        ]

        cls.devices = [
            create_test_device(name='ZabbixServer Assignment Test Device 1'),
            create_test_device(name='ZabbixServer Assignment Test Device 2'),
            create_test_device(name='ZabbixServer Assignment Test Device 3'),
            create_test_device(name='ZabbixServer Assignment Test Device 4'),
        ]
        cls.virtualmachines = [create_test_virtualmachine(name='VM1')]

        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.vm_ct = ContentType.objects.get_for_model(VirtualMachine)

        cls.assignments = [
            ZabbixServerAssignment.objects.create(
                zabbixserver=cls.zabbix_servers[0],
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[0].id,
            ),
            ZabbixServerAssignment.objects.create(
                zabbixserver=cls.zabbix_servers[1],
                assigned_object_type=cls.vm_ct,
                assigned_object_id=cls.virtualmachines[0].id,
            ),
        ]

    def test_filter_by_q(self):
        f = ZabbixServerAssignmentFilterSet({'q': 'Bulk 1'}, queryset=self.queryset)
        self.assertEqual(f.qs.count(), 1)
        self.assertEqual(f.qs.first().zabbixserver.name, 'Zabbix Server Bulk 1')

    def test_filter_by_zabbixserver_name(self):
        f = ZabbixServerAssignmentFilterSet({'zabbixserver_name': 'Bulk 2'}, queryset=self.queryset)
        self.assertEqual(f.qs.count(), 1)
        self.assertEqual(f.qs.first().zabbixserver.name, 'Zabbix Server Bulk 2')

    def test_filter_proxy_placeholder(self):
        f = ZabbixServerAssignmentFilterSet({'zabbixproxy_name': 'ProxyX'}, queryset=self.queryset)
        self.assertEqual(f.qs.count(), 0)

    def test_filter_proxygroup_placeholder(self):
        f = ZabbixServerAssignmentFilterSet({'zabbixproxygroup_name': 'GroupY'}, queryset=self.queryset)
        self.assertEqual(f.qs.count(), 0)

    def test_search_method_blank_input(self):
        fs = ZabbixServerAssignmentFilterSet({}, queryset=self.queryset)
        self.assertEqual(list(fs.search(self.queryset, 'q', '')), list(self.queryset))
        self.assertEqual(list(fs.search(self.queryset, 'q', '   ')), list(self.queryset))

    def test_filter_by_assigned_object_type(self):
        f = ZabbixServerAssignmentFilterSet({'assigned_object_type': f'{self.device_ct.app_label}.{self.device_ct.model}'}, queryset=ZabbixServerAssignment.objects.all())
        self.assertEqual(f.qs.count(), 1)

    def test_filter_fails_with_wrong_content_type(self):
        wrong_ct = ContentType.objects.get_for_model(ZabbixTag)
        f = ZabbixServerAssignmentFilterSet(
            {'assigned_object_type': f'{wrong_ct.app_label}.{wrong_ct.model}', 'assigned_object_id': self.devices[0].id},
            queryset=ZabbixServerAssignment.objects.all(),
        )
        self.assertEqual(f.qs.count(), 0)

    def test_filter_by_assigned_object_id_alone(self):
        f = ZabbixServerAssignmentFilterSet({'assigned_object_id': self.devices[0].id}, queryset=ZabbixServerAssignment.objects.all())
        self.assertIn(self.assignments[0], f.qs)
        self.assertNotIn(self.assignments[1], f.qs)

    def test_search_numeric_value_matches_hostid(self):
        # Create an assignment that has a hostid set
        assignment_with_hostid = ZabbixServerAssignment.objects.create(
            zabbixserver=self.zabbix_servers[2],
            assigned_object_type=self.device_ct,
            assigned_object_id=self.devices[2].id,
            hostid=555123,
        )

        # Sanity: another assignment without this hostid should not be returned
        _ = ZabbixServerAssignment.objects.create(
            zabbixserver=self.zabbix_servers[0],
            assigned_object_type=self.device_ct,
            assigned_object_id=self.devices[3].id,
            hostid=999999,
        )

        f = ZabbixServerAssignmentFilterSet({'q': '555123'}, queryset=ZabbixServerAssignment.objects.all())
        self.assertIn(assignment_with_hostid, f.qs)
        # Ensure we only matched by hostid, not by names
        self.assertEqual(f.qs.count(), 1)
        self.assertEqual(f.qs.first().hostid, 555123)
