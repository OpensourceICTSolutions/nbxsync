from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from ipam.models import IPAddress

from dcim.models import Device, Site
from utilities.testing import create_test_device

from nbxsync.choices import ZabbixProxyTypeChoices, ZabbixTLSChoices
from nbxsync.choices.zabbixstatus import ZabbixHostStatus
from nbxsync.jobs.synchost import SyncHostJob
from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixHostInterface, ZabbixProxy, ZabbixProxyGroup, ZabbixServer, ZabbixServerAssignment
from nbxsync.utils.sync import ProxyGroupSync
from nbxsync.settings import get_plugin_settings


class SyncHostJobTestCase(TestCase):
    def setUp(self):
        get_plugin_settings().trigger_dependencies.enabled = False

        self.device = create_test_device(name='SyncHostVM')
        self.device_ct = ContentType.objects.get_for_model(Device)

        self.zabbixserver = ZabbixServer.objects.create(name='Zabbix1', url='http://zabbix.local', token='abc123')

        self.proxygroup = ZabbixProxyGroup.objects.create(failover_delay='1m', name='Test Proxy Group123', zabbixserver=self.zabbixserver, proxy_groupid=99)
        self.proxy = ZabbixProxy.objects.create(
            name='Active Proxy #1',
            zabbixserver=self.zabbixserver,
            proxygroup=self.proxygroup,
            operating_mode=ZabbixProxyTypeChoices.ACTIVE,
            local_address='192.168.1.1',
            local_port=10051,
            allowed_addresses=['10.0.0.1'],
            tls_accept=[ZabbixTLSChoices.PSK],
            tls_psk_identity='psk-id',
            tls_psk='2AB09AD2496109A3BFAC0C6BB4D37CEF',
        )

        self.hostgroup = ZabbixHostgroup.objects.create(name='HG1', zabbixserver=self.zabbixserver, groupid=123, value='Static Group')
        self.interface_ip = IPAddress.objects.create(address='192.168.1.100/32')
        self.hostinterface = ZabbixHostInterface.objects.create(
            zabbixserver=self.zabbixserver,
            type=1,
            interface_type=1,
            useip=1,
            dns='',
            ip=self.interface_ip,
            port=10050,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )
        self.zabbixserverassignment = ZabbixServerAssignment.objects.create(
            zabbixserver=self.zabbixserver,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
            hostid='12345',
            zabbixproxy=self.proxy,
        )

        self.zabbixhostgroupassignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)

        # Patch ZabbixConnection to avoid real HTTP calls
        self.zabbix_patcher = patch('nbxsync.utils.sync.run_zabbix_operations.ZabbixConnection')
        mock_conn_class = self.zabbix_patcher.start()
        self.addCleanup(self.zabbix_patcher.stop)

        # Define a stable mock API
        mock_api = MagicMock()
        mock_api.host.get.return_value = [{'hostid': '12345'}]
        mock_api.host.create.return_value = {'hostids': ['12345']}
        mock_api.host.update.return_value = {'hostids': ['12345']}
        mock_api.host.delete.return_value = True
        mock_api.hostinterface.get.return_value = []
        mock_api.hostinterface.create.return_value = {'interfaceids': ['999']}
        mock_api.proxy.get.return_value = [
            {
                'proxyid': '42',
                'host': 'Active Proxy #1',
                'status': '5',
                'description': 'Desc',
                'tls_accept': '1',
                'tls_connect': '1',
                'tls_psk': 'psk',
                'tls_psk_identity': 'id',
                'proxy_groupid': '99',
                'local_address': '192.168.1.1',
                'local_port': '10051',
                'allowed_addresses': '10.0.0.1',
                'address': '127.0.0.1',
                'port': '10051',
            }
        ]
        mock_api.hostgroup.get.return_value = [{'groupid': '1'}]
        mock_api.proxygroup.get.return_value = [{'proxy_groupid': 99, 'failover_delay': '1m', 'min_online': 1}]
        mock_api.proxygroup.create.return_value = {'proxy_groupids': [99]}

        # Assign API to context manager return
        mock_conn_class.return_value.__enter__.return_value = mock_api

    def test_run_sync_host_success(self):
        job = SyncHostJob(instance=self.device)
        job.run()

    @patch('nbxsync.jobs.synchost.sync_device_trigger_dependencies')
    def test_run_skips_trigger_dependency_sync_by_default(self, mock_sync_dependencies):
        job = SyncHostJob(instance=self.device)
        job.run()

        mock_sync_dependencies.assert_not_called()

    @patch('nbxsync.jobs.synchost.sync_device_trigger_dependencies')
    def test_run_syncs_trigger_dependencies_when_enabled(self, mock_sync_dependencies):
        get_plugin_settings().trigger_dependencies.enabled = True

        job = SyncHostJob(instance=self.device)
        job.run()

        mock_sync_dependencies.assert_called_once_with(self.device)

    @patch('nbxsync.jobs.synchost.sync_device_trigger_dependencies')
    def test_run_swallows_trigger_dependency_sync_exception(self, mock_sync_dependencies):
        """A Zabbix API failure inside dep sync must not fail the surrounding host sync."""
        get_plugin_settings().trigger_dependencies.enabled = True
        mock_sync_dependencies.side_effect = Exception('Zabbix API timeout')

        job = SyncHostJob(instance=self.device)

        with self.assertLogs('nbxsync.jobs.synchost', level='ERROR') as log_ctx:
            job.run()  # must not raise

        mock_sync_dependencies.assert_called_once_with(self.device)
        log_text = '\n'.join(log_ctx.output)
        self.assertIn('Zabbix API timeout', log_text)

    def test_run_sync_host_deleted(self):
        self.device.status = 'decommissioning'
        self.device.save()
        # Set mapping to deleted for test
        pluginsettings = get_plugin_settings()
        pluginsettings.statusmapping.device['decommissioning'] = ZabbixHostStatus.DELETED

        job = SyncHostJob(instance=self.device)
        job.run()

    def test_sync_host_with_no_proxy_or_group(self):
        self.zabbixserverassignment.zabbixproxy = None
        self.zabbixserverassignment.zabbixproxygroup = None
        self.zabbixserverassignment.save()

        job = SyncHostJob(instance=self.device)
        job.run()

    @patch('nbxsync.jobs.synchost.safe_sync')
    @patch.object(SyncHostJob, 'verify_hostinterfaces')  # Prevent interface verification from running
    def test_sync_host_with_proxygroup(self, mock_verify_interfaces, mock_safe_sync):
        self.zabbixserverassignment.zabbixproxy = None
        self.zabbixserverassignment.zabbixproxygroup = self.proxygroup
        self.zabbixserverassignment.save()

        job = SyncHostJob(instance=self.device)
        job.run()

        called_types = [call.args[0] for call in mock_safe_sync.call_args_list]
        self.assertIn(ProxyGroupSync, called_types)

    @patch('nbxsync.jobs.synchost.safe_sync')
    @patch.object(SyncHostJob, 'verify_hostinterfaces')  # prevent irrelevant logic from running
    def test_sync_host_raises_runtimeerror_on_exception(self, mock_verify_interfaces, mock_safe_sync):
        # Force safe_sync to raise an error (e.g., during HostGroupSync)
        mock_safe_sync.side_effect = ValueError('Simulated failure')

        job = SyncHostJob(instance=self.device)

        with self.assertRaises(RuntimeError) as context:
            job.run()

        self.assertIn('Unexpected error: Simulated failure', str(context.exception))

    @patch('nbxsync.jobs.synchost.safe_sync')
    @patch.object(SyncHostJob, 'verify_hostinterfaces')
    def test_sync_host_hostsync_exception_is_swallowed(self, mock_verify_interfaces, mock_safe_sync):
        hostsync_call_count = {'count': 0}

        def side_effect(sync_class, *args, **kwargs):
            if getattr(sync_class, '__name__', None) == 'HostSync':
                if hostsync_call_count['count'] == 0:
                    hostsync_call_count['count'] += 1
                    raise Exception('Simulated HostSync failure')
                hostsync_call_count['count'] += 1
                return None
            return None

        mock_safe_sync.side_effect = side_effect

        job = SyncHostJob(instance=self.device)

        with patch('nbxsync.jobs.synchost.get_assigned_zabbixobjects') as mock_gao:
            mock_gao.return_value = {
                'hostgroups': [],
                'hostinterfaces': [self.hostinterface],
                'server_assignments': [self.zabbixserverassignment],
                'templates': [],
                'macros': [],
                'tags': [],
                'hostinventory': None,
                'configurationgroup': None,
            }

            job.run()

        self.assertGreaterEqual(hostsync_call_count['count'], 2)

        interface_sync_called = any(getattr(call.args[0], '__name__', None) == 'HostInterfaceSync' for call in mock_safe_sync.call_args_list)
        self.assertTrue(interface_sync_called)

    @patch('nbxsync.jobs.synchost.safe_sync')
    def test_run_skips_sync_when_assignment_sync_disabled(self, mock_safe_sync):
        self.zabbixserverassignment.sync_enabled = False
        self.zabbixserverassignment.save()

        job = SyncHostJob(instance=self.device)
        job.run()

        mock_safe_sync.assert_not_called()

    @patch('nbxsync.jobs.synchost.safe_sync')
    def test_run_skips_sync_when_zabbixserver_sync_disabled(self, mock_safe_sync):
        self.zabbixserver.sync_enabled = False
        self.zabbixserver.save()

        job = SyncHostJob(instance=self.device)
        job.run()

        mock_safe_sync.assert_not_called()

    @patch('nbxsync.jobs.synchost.safe_sync')
    def test_run_skips_sync_when_both_assignment_and_zabbixserver_sync_disabled(self, mock_safe_sync):
        self.zabbixserverassignment.sync_enabled = False
        self.zabbixserverassignment.save()
        self.zabbixserver.sync_enabled = False
        self.zabbixserver.save()

        job = SyncHostJob(instance=self.device)
        job.run()

        mock_safe_sync.assert_not_called()

    def test_prepare_assignment_returns_original_for_direct(self):
        job = SyncHostJob(instance=self.device)

        prepared = job._prepare_assignment(self.zabbixserverassignment)

        self.assertEqual(prepared.pk, self.zabbixserverassignment.pk)
        self.assertFalse(getattr(prepared, '_is_inherited_copy', False))

    def test_prepare_assignment_copies_inherited(self):
        site = self.device.site
        site_ct = ContentType.objects.get_for_model(Site)

        site_assignment = ZabbixServerAssignment.objects.create(
            zabbixserver=self.zabbixserver,
            assigned_object_type=site_ct,
            assigned_object_id=site.pk,
            zabbixproxy=self.proxy,
        )

        job = SyncHostJob(instance=self.device)
        prepared = job._prepare_assignment(site_assignment)

        self.assertIsNone(prepared.pk)
        self.assertTrue(getattr(prepared, '_is_inherited_copy', False))
        # Original assignment is untouched
        self.assertIsNotNone(site_assignment.pk)

    @patch('nbxsync.jobs.synchost.safe_sync')
    @patch.object(SyncHostJob, 'verify_hostinterfaces')
    @patch.object(SyncHostJob, 'check_default_hostinterface')
    def test_run_syncs_inherited_assignment_from_site(self, mock_check, mock_verify, mock_safe_sync):
        site = self.device.site
        site_ct = ContentType.objects.get_for_model(Site)

        # Remove the direct assignment so only inherited remains
        self.zabbixserverassignment.delete()

        ZabbixServerAssignment.objects.create(
            zabbixserver=self.zabbixserver,
            assigned_object_type=site_ct,
            assigned_object_id=site.pk,
            zabbixproxy=self.proxy,
        )

        job = SyncHostJob(instance=self.device)
        job.run()

        # safe_sync should have been called (host groups, proxy, host, interfaces)
        self.assertTrue(mock_safe_sync.called)

    @patch('nbxsync.jobs.synchost.safe_sync')
    def test_run_continues_when_assignment_sync_disabled(self, mock_safe_sync):
        # Create two assignments: one disabled (site-level), one enabled (direct)
        site = self.device.site
        site_ct = ContentType.objects.get_for_model(Site)

        ZabbixServerAssignment.objects.create(
            zabbixserver=self.zabbixserver,
            assigned_object_type=site_ct,
            assigned_object_id=site.pk,
            zabbixproxy=self.proxy,
            sync_enabled=False,
        )

        job = SyncHostJob(instance=self.device)
        job.run()

        # Direct assignment is enabled, so safe_sync should still be called
        self.assertTrue(mock_safe_sync.called)

    @patch('nbxsync.jobs.synchost.safe_sync')
    @patch.object(SyncHostJob, 'verify_hostinterfaces')
    def test_interface_sync_typeerror_propagates(self, mock_verify_interfaces, mock_safe_sync):
        """A TypeError from HostInterfaceSync propagates (programming errors are not swallowed)."""
        call_log = {'hostiface_calls': 0}

        def side_effect(sync_class, *args, **kwargs):
            name = getattr(sync_class, '__name__', None)
            if name == 'HostInterfaceSync':
                call_log['hostiface_calls'] += 1
                raise TypeError('bad argument')
            return None

        mock_safe_sync.side_effect = side_effect

        job = SyncHostJob(instance=self.device)

        with patch('nbxsync.jobs.synchost.get_assigned_zabbixobjects') as mock_gao:
            mock_gao.return_value = {
                'hostgroups': [],
                'hostinterfaces': [self.hostinterface],
                'server_assignments': [self.zabbixserverassignment],
                'templates': [],
                'macros': [],
                'tags': [],
                'hostinventory': None,
                'configurationgroup': None,
            }

            with self.assertRaises(RuntimeError) as context:
                job.run()

        self.assertIn('Unexpected error', str(context.exception))
        self.assertGreater(call_log['hostiface_calls'], 0)

    @patch('nbxsync.jobs.synchost.safe_sync')
    @patch.object(SyncHostJob, 'verify_hostinterfaces')
    def test_interface_sync_runtimeerror_continues_then_reports(self, mock_verify_interfaces, mock_safe_sync):
        """A RuntimeError from HostInterfaceSync does not stop the remaining work, but the job still fails.

        Independent work (other interfaces, the final template linkage, binding
        retirement) must complete, and the recoverable failure must be reported
        as an aggregated error so a host with a missing interface cannot be
        mistaken for a successful reconciliation.
        """
        call_log = {'hostiface_calls': 0, 'hostsync_calls': 0}

        def side_effect(sync_class, *args, **kwargs):
            name = getattr(sync_class, '__name__', None)
            if name == 'HostInterfaceSync':
                call_log['hostiface_calls'] += 1
                raise RuntimeError('Error syncing HostInterfaceSync: SNMP credentials wrong')
            if name == 'HostSync':
                call_log['hostsync_calls'] += 1
            return None

        mock_safe_sync.side_effect = side_effect

        job = SyncHostJob(instance=self.device)

        with patch('nbxsync.jobs.synchost.get_assigned_zabbixobjects') as mock_gao:
            mock_gao.return_value = {
                'hostgroups': [],
                'hostinterfaces': [self.hostinterface],
                'server_assignments': [self.zabbixserverassignment],
                'templates': [],
                'macros': [],
                'tags': [],
                'hostinventory': None,
                'configurationgroup': None,
            }

            with self.assertRaises(RuntimeError) as context:
                job.run()

        self.assertIn('Partial sync failure', str(context.exception))
        self.assertIn('SNMP credentials wrong', str(context.exception))
        self.assertGreater(call_log['hostiface_calls'], 0)
        # The final HostSync still ran after the interface failure.
        self.assertGreaterEqual(call_log['hostsync_calls'], 2)
