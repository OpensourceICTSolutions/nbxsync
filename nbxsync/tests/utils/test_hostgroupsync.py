from unittest.mock import MagicMock

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixServer
from nbxsync.utils.sync.hostgroupsync import HostGroupSync


class HostGroupSyncIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.device = create_test_device(name='HG Sync TestDev1')

        cls.zabbixserver = ZabbixServer.objects.create(name='Zabbix A', url='http://zabbix.local', token='abc123', validate_certs=True)
        cls.hostgroups = [
            ZabbixHostgroup.objects.create(name='Static Group', groupid=123, zabbixserver=cls.zabbixserver, value='Static Group'),
            ZabbixHostgroup.objects.create(name='Dynamic Group', groupid=None, zabbixserver=cls.zabbixserver, value='HG {{ object.name }}'),
        ]

        cls.assignment_static = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=cls.hostgroups[0], assigned_object_type=cls.device_ct, assigned_object_id=cls.device.id)
        cls.assignment_dynamic = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=cls.hostgroups[1], assigned_object_type=cls.device_ct, assigned_object_id=cls.device.id)

    def test_get_name_value_static(self):
        sync = HostGroupSync(api=MagicMock(), netbox_obj=self.assignment_static)
        self.assertEqual(sync.get_name_value(), 'Static Group')

    def test_get_create_params_static(self):
        sync = HostGroupSync(api=MagicMock(), netbox_obj=self.assignment_static)
        self.assertEqual(sync.get_create_params(), {'name': 'Static Group'})

    def test_get_update_params_static(self):
        sync = HostGroupSync(api=MagicMock(), netbox_obj=self.assignment_static)
        expected = {'name': 'Static Group', 'groupid': 123}
        self.assertEqual(sync.get_update_params(), expected)

    def test_get_id_static(self):
        sync = HostGroupSync(api=MagicMock(), netbox_obj=self.assignment_static)
        self.assertEqual(sync.get_id(), 123)

    def test_get_id_dynamic_returns_none(self):
        sync = HostGroupSync(api=MagicMock(), netbox_obj=self.assignment_dynamic)
        self.assertIsNone(sync.get_id())

    def test_set_id_static_sets_groupid(self):
        sync = HostGroupSync(api=MagicMock(), netbox_obj=self.assignment_static)
        sync.set_id(999)
        self.assertEqual(self.assignment_static.zabbixhostgroup.groupid, 999)

    def test_set_id_dynamic_does_not_set(self):
        sync = HostGroupSync(api=MagicMock(), netbox_obj=self.assignment_dynamic)
        original = self.assignment_dynamic.zabbixhostgroup.groupid  # None
        sync.set_id(999)
        self.assertEqual(self.assignment_dynamic.zabbixhostgroup.groupid, original)  # still None

    def test_api_object_and_result_key(self):
        mock_api = MagicMock()
        sync = HostGroupSync(api=mock_api, netbox_obj=self.assignment_static)
        self.assertEqual(sync.api_object(), mock_api.hostgroup)
        self.assertEqual(sync.result_key(), 'groupids')

    def test_set_id_dynamic_updates_existing_hostgroup(self):
        existing_hg = ZabbixHostgroup.objects.create(name='ExistingGroup', groupid=999, zabbixserver=self.zabbixserver, value='ExistingGroup', description='Existing hostgroup to be updated')
        count_before = ZabbixHostgroup.objects.count()
        sync = HostGroupSync(api=None, netbox_obj=self.assignment_dynamic)
        sync.set_id(999)

        count_after = ZabbixHostgroup.objects.count()
        updated_hg = ZabbixHostgroup.objects.get(pk=existing_hg.pk)

        self.assertEqual(count_before, count_after)
        self.assertEqual(updated_hg.groupid, 999)
        self.assertEqual(updated_hg.name, 'ExistingGroup')
        self.assertEqual(updated_hg.zabbixserver, self.zabbixserver)
