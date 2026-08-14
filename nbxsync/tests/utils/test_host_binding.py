from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from utilities.testing import create_test_device

from nbxsync.models import ZabbixHostBinding, ZabbixServer, ZabbixServerAssignment
from nbxsync.utils.host_binding import HostBindingDeleteProxy, backfill_or_resolve_conflict
from nbxsync.utils.sync import HostSync


class PluginSettingMixin:
    """Temporarily override a validated plugin setting for one test."""

    def _set_plugin_setting(self, name, value):
        from nbxsync.settings import get_plugin_settings

        pluginsettings = get_plugin_settings()
        original = getattr(pluginsettings, name)
        setattr(pluginsettings, name, value)
        self.addCleanup(setattr, pluginsettings, name, original)


class HostBindingTestCase(PluginSettingMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix', url='http://zabbix.local', token='t')
        cls.device = create_test_device(name='binding-test')
        cls.device_ct = ContentType.objects.get_for_model(cls.device)
        cls.assignment = ZabbixServerAssignment.objects.create(
            zabbixserver=cls.server,
            assigned_object_type=cls.device_ct,
            assigned_object_id=cls.device.pk,
        )

    def _all_objects(self):
        return {
            'hostgroups': [],
            'tags': [],
            'macros': [],
            'hostinterfaces': [],
            'templates': [],
            'hostinventory': None,
            '_instance': self.device,
        }

    def _api(self, host_get=None):
        api = MagicMock()
        api.host.get.return_value = host_get if host_get is not None else []
        api.host.create.return_value = {'hostids': ['100']}
        api.host.update.return_value = {'hostids': ['100']}
        api.hostinterface.get.return_value = []
        api.template.get.return_value = []
        api.maintenance.get.return_value = []
        return api

    def _attach_assigned_objects(self, assignment):
        assignment.assigned_objects = self._all_objects()

    def test_inherited_creation_persists_binding(self):
        inherited = MagicMock()
        inherited.zabbixserver = self.server
        inherited.hostid = None
        inherited.assigned_object = self.device
        inherited.assigned_object_type = self.device_ct
        inherited.assigned_object_id = self.device.pk
        inherited._is_inherited_copy = True
        inherited.pk = None
        inherited.update_sync_info = MagicMock()
        inherited.assigned_objects = self._all_objects()

        api = self._api()
        sync = HostSync(api=api, netbox_obj=inherited, all_objects=self._all_objects())
        sync.sync()

        binding = ZabbixHostBinding.objects.get(assigned_object_id=self.device.pk, zabbixserver=self.server)
        self.assertEqual(binding.hostid, 100)

    def test_second_sync_uses_same_hostid(self):
        api = self._api()
        self._attach_assigned_objects(self.assignment)
        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        sync.sync()

        api.host.get.return_value = [{'hostid': '100', 'host': 'binding-test', 'name': 'binding-test'}]
        api.host.create.reset_mock()

        sync2 = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        self._attach_assigned_objects(self.assignment)
        sync2.sync()

        api.host.create.assert_not_called()
        binding = ZabbixHostBinding.objects.get(assigned_object_id=self.device.pk, zabbixserver=self.server)
        self.assertEqual(binding.hostid, 100)

    def test_rename_updates_same_hostid(self):
        api = self._api()
        self._attach_assigned_objects(self.assignment)
        HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects()).sync()

        self.device.name = 'renamed-binding-test'
        self.device.save()

        api.host.get.return_value = [{'hostid': '100', 'host': 'binding-test', 'name': 'binding-test'}]
        api.host.create.reset_mock()

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        self._attach_assigned_objects(self.assignment)
        sync.sync()

        binding = ZabbixHostBinding.objects.get(assigned_object_id=self.device.pk, zabbixserver=self.server)
        self.assertEqual(binding.hostid, 100)
        self.assertEqual(binding.hostname, 'renamed-binding-test')

    def test_unmanaged_same_name_conflict(self):
        def host_get(**kwargs):
            if kwargs.get('hostids'):
                return []
            if kwargs.get('filter', {}).get('host'):
                return [{'hostid': '200', 'host': 'binding-test', 'name': 'binding-test', 'tags': []}]
            return []

        api = MagicMock()
        api.host.get.side_effect = host_get
        self._attach_assigned_objects(self.assignment)

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        with self.assertRaises(RuntimeError):
            sync.sync()

    def test_adoption_looks_up_technical_hostname(self):
        self._set_plugin_setting('adopt_existing_hosts', True)
        api = MagicMock()
        api.host.get.return_value = [
            {
                'hostid': '321',
                'host': 'tech-host-01',
                'tags': [
                    {'tag': 'nb_type', 'value': 'device'},
                    {'tag': 'nb_id', 'value': str(self.device.pk)},
                ],
            }
        ]

        hostid = backfill_or_resolve_conflict(self.device, self.server, api, hostname='tech-host-01')

        self.assertEqual(hostid, 321)
        api.host.get.assert_called_with(filter={'host': 'tech-host-01'}, selectTags='extend')

    def test_duplicate_managed_identity_conflict(self):
        other_device = create_test_device(name='other-binding-test')
        ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=other_device.pk,
            hostid=777,
            hostname='other',
        )
        self.assignment.hostid = 777
        self.assignment.save()

        api = self._api(host_get=[{'hostid': '777', 'host': 'binding-test', 'name': 'binding-test'}])
        self._attach_assigned_objects(self.assignment)

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        with self.assertRaises(RuntimeError):
            sync.sync()

    def test_decommission_deletes_by_hostid(self):
        ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=100,
            hostname='binding-test',
        )
        api = self._api(host_get=[{'hostid': '100', 'host': 'binding-test', 'name': 'binding-test'}])
        self._attach_assigned_objects(self.assignment)

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        sync.delete()

        api.host.delete.assert_called_once_with([100])
        self.assertFalse(ZabbixHostBinding.objects.filter(assigned_object_id=self.device.pk, zabbixserver=self.server).exists())

    def test_missing_remote_host_is_idempotent(self):
        ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=999,
            hostname='binding-test',
        )
        api = self._api()
        self._attach_assigned_objects(self.assignment)

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        sync.sync()

        binding = ZabbixHostBinding.objects.get(assigned_object_id=self.device.pk, zabbixserver=self.server)
        self.assertEqual(binding.hostid, 100)

    def test_direct_assignment_hostid_migrates_to_binding(self):
        self.assignment.hostid = 222
        self.assignment.save()

        def host_get(**kwargs):
            if kwargs.get('hostids') == ['222']:
                return [{'hostid': '222', 'host': 'binding-test', 'name': 'binding-test'}]
            return []

        api = MagicMock()
        api.host.get.side_effect = host_get
        api.host.create.return_value = {'hostids': ['222']}
        api.host.update.return_value = {'hostids': ['222']}
        api.hostinterface.get.return_value = []
        api.template.get.return_value = []
        api.maintenance.get.return_value = []
        self._attach_assigned_objects(self.assignment)

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        sync.sync()

        binding = ZabbixHostBinding.objects.get(assigned_object_id=self.device.pk, zabbixserver=self.server)
        self.assertEqual(binding.hostid, 222)
        self.assignment.refresh_from_db()
        self.assertIsNone(self.assignment.hostid)

    def test_existing_hosts_backfill(self):
        self._set_plugin_setting('adopt_existing_hosts', True)

        def host_get(**kwargs):
            if kwargs.get('hostids'):
                return []
            if kwargs.get('filter', {}).get('host'):
                return [
                    {
                        'hostid': '300',
                        'host': 'binding-test',
                        'name': 'binding-test',
                        'tags': [
                            {'tag': 'nb_type', 'value': 'device'},
                            {'tag': 'nb_id', 'value': str(self.device.pk)},
                        ],
                    }
                ]
            return []

        api = MagicMock()
        api.host.get.side_effect = host_get
        api.hostinterface.get.return_value = []
        api.template.get.return_value = []
        api.maintenance.get.return_value = []
        self._attach_assigned_objects(self.assignment)

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        sync.sync()

        binding = ZabbixHostBinding.objects.get(assigned_object_id=self.device.pk, zabbixserver=self.server)
        self.assertEqual(binding.hostid, 300)

    def test_existing_host_is_not_adopted_by_default(self):
        """Without adopt_existing_hosts, an unbound managed host is a reported conflict."""

        def host_get(**kwargs):
            if kwargs.get('hostids'):
                return []
            if kwargs.get('filter', {}).get('host'):
                return [
                    {
                        'hostid': '300',
                        'host': 'binding-test',
                        'name': 'binding-test',
                        'tags': [
                            {'tag': 'nb_type', 'value': 'device'},
                            {'tag': 'nb_id', 'value': str(self.device.pk)},
                        ],
                    }
                ]
            return []

        api = MagicMock()
        api.host.get.side_effect = host_get
        api.hostinterface.get.return_value = []
        api.template.get.return_value = []
        api.maintenance.get.return_value = []
        self._attach_assigned_objects(self.assignment)

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        with self.assertRaises(RuntimeError) as context:
            sync.sync()

        self.assertIn('adopt_existing_hosts', str(context.exception))
        self.assertFalse(ZabbixHostBinding.objects.filter(assigned_object_id=self.device.pk, zabbixserver=self.server).exists())
        api.host.create.assert_not_called()

    def test_hard_delete_after_netbox_object_is_missing(self):
        binding = ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=9_000_001,
            hostid=4_000_000_001,
            hostname='deleted-binding-test',
        )
        proxy = HostBindingDeleteProxy(binding)
        api = self._api(host_get=[{'hostid': str(binding.hostid), 'host': binding.hostname}])

        HostSync(api=api, netbox_obj=proxy).delete()

        api.host.delete.assert_called_once_with([binding.hostid])
        self.assertFalse(ZabbixHostBinding.objects.filter(pk=binding.pk).exists())

    def test_hard_delete_failure_retains_binding(self):
        binding = ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=9_000_002,
            hostid=4_000_000_002,
            hostname='retry-binding-test',
        )
        proxy = HostBindingDeleteProxy(binding)
        api = self._api(host_get=[{'hostid': str(binding.hostid), 'host': binding.hostname}])
        api.host.delete.side_effect = RuntimeError('temporary Zabbix failure')

        with self.assertRaises(RuntimeError):
            HostSync(api=api, netbox_obj=proxy).delete()

        self.assertTrue(ZabbixHostBinding.objects.filter(pk=binding.pk).exists())

    def test_hard_delete_missing_remote_is_idempotent(self):
        binding = ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=9_000_003,
            hostid=4_000_000_003,
            hostname='missing-binding-test',
        )
        proxy = HostBindingDeleteProxy(binding)
        api = self._api(host_get=[])

        HostSync(api=api, netbox_obj=proxy).delete()

        api.host.delete.assert_not_called()
        self.assertFalse(ZabbixHostBinding.objects.filter(pk=binding.pk).exists())


class BindingJobTestCase(PluginSettingMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix', url='http://zabbix.local', token='t')
        cls.device = create_test_device(name='binding-job-test')
        cls.device_ct = ContentType.objects.get_for_model(cls.device)

    def test_deletejob_uses_stable_binding_id(self):
        binding = ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=888,
            hostname='binding-job-test',
        )

        from nbxsync.jobs.deletehost import DeleteHostJob

        with patch('nbxsync.jobs.deletehost.safe_delete') as mock_safe_delete:
            DeleteHostJob(binding_ids=[binding.pk]).run()

        self.assertEqual(mock_safe_delete.call_count, 1)
        proxy = mock_safe_delete.call_args[0][1]
        self.assertIsInstance(proxy, HostBindingDeleteProxy)
        self.assertEqual(proxy.binding_id, binding.pk)
        self.assertEqual(proxy.hostid, 888)
        self.assertTrue(ZabbixHostBinding.objects.filter(pk=binding.pk).exists())

    def test_deletejob_failure_keeps_binding_and_raises_for_retry(self):
        binding = ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=889,
            hostname='binding-job-test',
        )

        from nbxsync.jobs.deletehost import DeleteHostJob

        with patch('nbxsync.jobs.deletehost.safe_delete', side_effect=RuntimeError('temporary failure')):
            with self.assertRaises(RuntimeError):
                DeleteHostJob(binding_ids=[binding.pk]).run()

        self.assertTrue(ZabbixHostBinding.objects.filter(pk=binding.pk).exists())

    def test_retire_unassigned_bindings(self):
        self._set_plugin_setting('allow_inherited_deletion', True)
        binding = ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=555,
            hostname='binding-job-test',
        )

        from nbxsync.jobs.synchost import SyncHostJob

        with patch('nbxsync.jobs.synchost.safe_delete') as mock_safe_delete:
            job = SyncHostJob(instance=self.device)
            job._retire_unassigned_bindings(set())

        mock_safe_delete.assert_called_once()
        proxy = mock_safe_delete.call_args[0][1]
        self.assertIsInstance(proxy, HostBindingDeleteProxy)
        self.assertEqual(proxy.zabbixserver, self.server)
        self.assertEqual(proxy.hostid, binding.hostid)
        self.assertEqual(proxy.assigned_object, self.device)

    def test_unassigned_binding_is_kept_when_inherited_deletion_disabled(self):
        """The default configuration reports the impact instead of deleting the host."""
        binding = ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=556,
            hostname='binding-job-test',
        )

        from nbxsync.jobs.synchost import SyncHostJob

        with patch('nbxsync.jobs.synchost.safe_delete') as mock_safe_delete:
            with self.assertLogs('nbxsync.jobs.synchost', level='WARNING') as logs:
                job = SyncHostJob(instance=self.device)
                job._retire_unassigned_bindings(set())

        mock_safe_delete.assert_not_called()
        self.assertIn('allow_inherited_deletion', ' '.join(logs.output))
        self.assertTrue(ZabbixHostBinding.objects.filter(pk=binding.pk).exists())


class ManagedHostIdentityTestCase(TestCase):
    """get_managed_host_id / iter_managed_hosts after assignment.hostid is cleared."""

    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Identity Zabbix', url='http://zabbix.local', token='t')
        cls.disabled_server = ZabbixServer.objects.create(name='Disabled Zabbix', url='http://zabbix-off.local', token='t', sync_enabled=False)
        cls.device = create_test_device(name='identity-test')
        cls.device_ct = ContentType.objects.get_for_model(cls.device)
        cls.assignment = ZabbixServerAssignment.objects.create(
            zabbixserver=cls.server,
            assigned_object_type=cls.device_ct,
            assigned_object_id=cls.device.pk,
        )

    def test_get_managed_host_id_prefers_binding_over_cleared_assignment(self):
        from nbxsync.utils.host_binding import get_managed_host_id

        self.assignment.hostid = None
        self.assignment.save()
        ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=4242,
            hostname='identity-test',
        )

        self.assertEqual(get_managed_host_id(self.device, self.server), 4242)

    def test_get_managed_host_id_falls_back_to_direct_assignment(self):
        from nbxsync.utils.host_binding import get_managed_host_id

        self.assignment.hostid = 777
        self.assignment.save()

        self.assertEqual(get_managed_host_id(self.device, self.server), 777)

    def test_get_managed_host_id_ignores_inherited_assignment_hostid(self):
        from dcim.models import Site

        from nbxsync.utils.host_binding import get_managed_host_id

        site = self.device.site
        site_ct = ContentType.objects.get_for_model(Site)
        ZabbixServerAssignment.objects.create(
            zabbixserver=self.server,
            assigned_object_type=site_ct,
            assigned_object_id=site.pk,
            hostid=9999,
        )
        self.assignment.delete()

        self.assertIsNone(get_managed_host_id(self.device, self.server))

    def test_iter_managed_hosts_finds_inherited_binding(self):
        from dcim.models import Site

        from nbxsync.utils.host_binding import iter_managed_hosts

        site = self.device.site
        site_ct = ContentType.objects.get_for_model(Site)
        self.assignment.delete()
        ZabbixServerAssignment.objects.create(
            zabbixserver=self.server,
            assigned_object_type=site_ct,
            assigned_object_id=site.pk,
        )
        ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=8800,
            hostname='identity-test',
        )

        managed = list(iter_managed_hosts(self.device, require_hostid=True))
        self.assertEqual(len(managed), 1)
        self.assertEqual(managed[0].hostid, 8800)
        self.assertEqual(managed[0].zabbixserver_id, self.server.pk)

    def test_iter_managed_hosts_skips_disabled_server(self):
        from nbxsync.utils.host_binding import iter_managed_hosts

        ZabbixHostBinding.objects.create(
            zabbixserver=self.disabled_server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=1,
        )
        self.assertEqual(list(iter_managed_hosts(self.device, require_hostid=True)), [])

    def test_get_host_assignments_uses_binding_after_hostid_cleared(self):
        from nbxsync.utils.trigger_dependency_sync import get_host_assignments

        self.assignment.hostid = None
        self.assignment.save()
        ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=5150,
            hostname='identity-test',
        )

        result = get_host_assignments(self.device)
        self.assertEqual(result[self.server.pk].hostid, 5150)
