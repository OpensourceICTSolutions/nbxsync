from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from ipam.models import IPAddress

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.choices import ZabbixProxyTypeChoices, ZabbixTLSChoices
from nbxsync.choices.zabbixstatus import ZabbixHostStatus
from nbxsync.jobs.synchost import SyncHostJob
from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixHostInterface, ZabbixProxy, ZabbixProxyGroup, ZabbixServer, ZabbixServerAssignment
from nbxsync.utils.sync import HostSync, ProxyGroupSync, HostInterfaceSync


class SyncHostJobTestCase(TestCase):
    def setUp(self):
        self.device = create_test_device(name='SyncHostVM')
        self.device_ct = ContentType.objects.get_for_model(Device)

        self.zabbixserver = ZabbixServer.objects.create(name='Zabbix1', url='http://zabbix.local', token='abc123')

        self.proxygroup = ZabbixProxyGroup.objects.create(name='Test Proxy Group', zabbixserver=self.zabbixserver, proxy_groupid=99)
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
        mock_api.proxygroup.get.return_value = [{'proxy_groupid': 99}]
        mock_api.proxygroup.create.return_value = {'proxy_groupids': [99]}

        # Assign API to context manager return
        mock_conn_class.return_value.__enter__.return_value = mock_api

    def test_run_sync_host_success(self):
        job = SyncHostJob(instance=self.device)
        job.run()

    def test_run_sync_host_deleted(self):
        self.device.status = 'decommissioning'
        self.device.save()
        # Set mapping to deleted for test
        from nbxsync.settings import get_plugin_settings

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
            }

            job.run()

        self.assertGreaterEqual(hostsync_call_count['count'], 2)

        interface_sync_called = any(getattr(call.args[0], '__name__', None) == 'HostInterfaceSync' for call in mock_safe_sync.call_args_list)
        self.assertTrue(interface_sync_called)
