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

    # def test_set_id_dynamic_does_not_set(self):
    #     sync = HostGroupSync(api=MagicMock(), netbox_obj=self.assignment_dynamic)
    #     original = self.assignment_dynamic.zabbixhostgroup.groupid  # None
    #     sync.set_id(999)

    #     self.assertEqual(self.assignment_dynamic.zabbixhostgroup.groupid, original)  # still None

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

    def test_set_id_dynamic_creates_rendered_hostgroup_when_missing(self):
        rendered_name, ok = self.assignment_dynamic.render()
        self.assertTrue(ok)

        sync = HostGroupSync(api=None, netbox_obj=self.assignment_dynamic)
        sync.set_id(321)

        created_hg = ZabbixHostgroup.objects.get(zabbixserver=self.zabbixserver, name=rendered_name)
        self.assertEqual(created_hg.value, rendered_name)
        self.assertEqual(created_hg.groupid, 321)
        self.assertEqual(created_hg.description, 'Automatically generated from template')


class HostGroupSyncNestedTests(TestCase):
    """Nested hostgroup names ('A/B/C') must materialize parents before the leaf.

    Zabbix only inherits user-group permissions/tag filters into a subgroup
    when its parent already exists; subgroup-only creation leaves phantom
    parents that can never hold permissions.
    """

    @classmethod
    def setUpTestData(cls):
        cls.zabbixserver = ZabbixServer.objects.create(name='Zabbix Nested', url='http://zabbix-nested.local', token='abc123', validate_certs=True)
        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.device = create_test_device(name='Nested Hostgroup TestDev')

    def _nested_assignment(self, name):
        hostgroup = ZabbixHostgroup.objects.create(name=name, zabbixserver=self.zabbixserver, value=name)
        return ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)

    def test_try_create_nested_creates_parents_before_leaf(self):
        from unittest.mock import call

        api = MagicMock()
        api.hostgroup.get.return_value = []
        api.hostgroup.create.side_effect = [{'groupids': [10]}, {'groupids': [11]}, {'groupids': [12]}]

        sync = HostGroupSync(api=api, netbox_obj=self._nested_assignment('Parent/Child/Leaf'))
        self.assertEqual(sync.try_create(), 12)

        self.assertEqual(
            api.hostgroup.create.call_args_list,
            [
                call({'name': 'Parent'}),
                call({'name': 'Parent/Child'}),
                call(name='Parent/Child/Leaf'),
            ],
        )

    def test_try_create_nested_idempotent_when_parents_exist(self):
        api = MagicMock()
        api.hostgroup.get.return_value = [{'groupid': '10', 'name': 'Parent'}]
        api.hostgroup.create.return_value = {'groupids': [12]}

        assignment = self._nested_assignment('Parent/Child')
        sync = HostGroupSync(api=api, netbox_obj=assignment)
        sync.try_create()

        # Parents found -> only the leaf is created
        self.assertEqual(api.hostgroup.create.call_count, 1)
        api.hostgroup.create.assert_called_once_with(name='Parent/Child')

    def test_try_create_flat_name_skips_parent_logic(self):
        api = MagicMock()
        api.hostgroup.create.return_value = {'groupids': [5]}

        assignment = self._nested_assignment('FlatGroup')
        sync = HostGroupSync(api=api, netbox_obj=assignment)
        sync.try_create()

        api.hostgroup.get.assert_not_called()
        api.hostgroup.create.assert_called_once_with(name='FlatGroup')

    def test_try_create_malformed_name_leaves_rejection_to_zabbix(self):
        """Empty segments / stray slashes are not our problem to fix silently:
        we skip parent logic and let the Zabbix API reject the leaf create."""
        api = MagicMock()
        api.hostgroup.create.side_effect = RuntimeError('invalid group name')

        assignment = self._nested_assignment('A//B')
        sync = HostGroupSync(api=api, netbox_obj=assignment)

        with self.assertRaises(RuntimeError):
            sync.try_create()
        # No parents were probed/created for the malformed name
        api.hostgroup.get.assert_not_called()
        self.assertEqual(api.hostgroup.create.call_count, 1)


class HostGroupSyncRenameTests(TestCase):
    """Renames must flow through hostgroup.update with the stored groupid."""

    @classmethod
    def setUpTestData(cls):
        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.device = create_test_device(name='Rename TestDev')
        cls.zabbixserver = ZabbixServer.objects.create(name='Zabbix Rename', url='http://zabbix-rename.local', token='abc123', validate_certs=True)
        cls.hostgroup = ZabbixHostgroup.objects.create(name='Static Group', groupid=123, zabbixserver=cls.zabbixserver, value='Static Group')
        cls.assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=cls.hostgroup, assigned_object_type=cls.device_ct, assigned_object_id=cls.device.id)

    def test_static_rename_updates_in_place_keeping_groupid(self):
        self.hostgroup.value = 'Renamed Static Group'
        self.hostgroup.name = 'Renamed Static Group'
        self.hostgroup.save()
        sync = HostGroupSync(api=MagicMock(), netbox_obj=self.assignment)
        self.assertEqual(sync.get_update_params(), {'name': 'Renamed Static Group', 'groupid': 123})
