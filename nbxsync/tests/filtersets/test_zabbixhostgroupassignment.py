from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.filtersets import ZabbixHostgroupAssignmentFilterSet
from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixServer, ZabbixTag


class ZabbixHostgroupAssignmentFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.devices = [
            create_test_device(name='Device A'),
            create_test_device(name='Device B'),
        ]

        cls.servers = [
            ZabbixServer.objects.create(
                name='Server A',
                url='http://a.example.com',
                token='token-a',
                validate_certs=True,
            ),
            ZabbixServer.objects.create(
                name='Server B',
                url='http://b.example.com',
                token='token-b',
                validate_certs=True,
            ),
        ]

        cls.hostgroups = [
            ZabbixHostgroup.objects.create(
                name='Linux Servers',
                description='All Linux hosts',
                value='group-linux',
                groupid=101,
                zabbixserver=cls.servers[0],
            ),
            ZabbixHostgroup.objects.create(
                name='Database Servers',
                description='DB hosts',
                value='group-db',
                groupid=202,
                zabbixserver=cls.servers[1],
            ),
        ]
        cls.assignments = [
            ZabbixHostgroupAssignment.objects.create(
                zabbixhostgroup=cls.hostgroups[0],
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[0].id,
            ),
            ZabbixHostgroupAssignment.objects.create(
                zabbixhostgroup=cls.hostgroups[1],
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[1].id,
            ),
        ]

    def test_search_by_group_name(self):
        f = ZabbixHostgroupAssignmentFilterSet({'q': 'Linux Servers'}, queryset=ZabbixHostgroupAssignment.objects.all())
        self.assertIn(self.assignments[0], f.qs)

    def test_search_blank_returns_all(self):
        f = ZabbixHostgroupAssignmentFilterSet({'q': '   '}, queryset=ZabbixHostgroupAssignment.objects.all())
        self.assertEqual(f.qs.count(), 2)

    def test_filter_by_group_name_field(self):
        f = ZabbixHostgroupAssignmentFilterSet({'zabbixhostgroup_name': 'Database Servers'}, queryset=ZabbixHostgroupAssignment.objects.all())
        self.assertIn(self.assignments[1], f.qs)

    def test_search_method_direct_call_hits_return_queryset(self):
        queryset = ZabbixHostgroupAssignment.objects.all()
        f = ZabbixHostgroupAssignmentFilterSet({}, queryset=queryset)
        result = f.search(queryset, name='q', value='   ')
        self.assertQuerySetEqual(result.order_by('id'), queryset.order_by('id'), transform=lambda x: x)

    def test_filter_by_assigned_object_type(self):
        f = ZabbixHostgroupAssignmentFilterSet({'assigned_object_type': f'{self.device_ct.app_label}.{self.device_ct.model}'}, queryset=ZabbixHostgroupAssignment.objects.all())
        self.assertEqual(f.qs.count(), 2)

    def test_filter_fails_with_wrong_content_type(self):
        wrong_ct = ContentType.objects.get_for_model(ZabbixTag)
        f = ZabbixHostgroupAssignmentFilterSet(
            {'assigned_object_type': f'{wrong_ct.app_label}.{wrong_ct.model}', 'assigned_object_id': self.devices[0].id},
            queryset=ZabbixHostgroupAssignment.objects.all(),
        )
        self.assertEqual(f.qs.count(), 0)

    def test_filter_by_assigned_object_id_alone(self):
        f = ZabbixHostgroupAssignmentFilterSet({'assigned_object_id': self.devices[0].id}, queryset=ZabbixHostgroupAssignment.objects.all())
        self.assertIn(self.assignments[0], f.qs)
        self.assertNotIn(self.assignments[1], f.qs)
