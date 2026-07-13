from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from ipam.models import IPAddress

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.choices import ZabbixProxyTypeChoices, ZabbixTLSChoices
from nbxsync.jobs.synchost import SyncHostJob
from nbxsync.models import (
    ZabbixHostgroup,
    ZabbixHostgroupAssignment,
    ZabbixHostInterface,
    ZabbixProxy,
    ZabbixServer,
    ZabbixServerAssignment,
    ZabbixTag,
    ZabbixTagAssignment,
)


class SyncHostExclusionTestCase(TestCase):
    """Tests for tag-based host exclusion (_is_excluded and exclude_tag)."""

    def setUp(self):
        self.device = create_test_device(name='ExcludeTestDevice')
        self.device_ct = ContentType.objects.get_for_model(Device)

        self.zabbixserver = ZabbixServer.objects.create(name='Zabbix1', url='http://zabbix.local', token='abc123')
        self.proxy = ZabbixProxy.objects.create(
            name='Test Proxy',
            zabbixserver=self.zabbixserver,
            operating_mode=ZabbixProxyTypeChoices.ACTIVE,
            local_address='192.168.1.1',
            local_port=10051,
            allowed_addresses=['10.0.0.1'],
            tls_accept=[ZabbixTLSChoices.PSK],
            tls_psk_identity='psk-id',
            tls_psk='2AB09AD2496109A3BFAC0C6BB4D37CEF',
        )
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
        self.hostgroup = ZabbixHostgroup.objects.create(name='HG1', zabbixserver=self.zabbixserver, groupid=123)
        self.zabbixserverassignment = ZabbixServerAssignment.objects.create(
            zabbixserver=self.zabbixserver,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
            hostid='12345',
            zabbixproxy=self.proxy,
        )
        self.zabbixhostgroupassignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=self.hostgroup,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )

        # Patch ZabbixConnection to avoid real HTTP calls
        self.zabbix_patcher = patch('nbxsync.utils.sync.run_zabbix_operations.ZabbixConnection')
        mock_conn_class = self.zabbix_patcher.start()
        self.addCleanup(self.zabbix_patcher.stop)

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
                'host': 'Test Proxy',
                'status': '5',
                'description': 'Desc',
                'tls_accept': '1',
                'tls_connect': '1',
                'tls_psk': 'psk',
                'tls_psk_identity': 'id',
                'proxy_groupid': '0',
                'local_address': '192.168.1.1',
                'local_port': '10051',
                'allowed_addresses': '10.0.0.1',
                'address': '127.0.0.1',
                'port': '10051',
            }
        ]
        mock_api.hostgroup.get.return_value = [{'groupid': '1'}]
        mock_conn_class.return_value.__enter__.return_value = mock_api

    def _create_exclude_tag(self):
        return ZabbixTag.objects.create(tag='do_not_monitor', name='Do Not Monitor', value='')

    @patch('nbxsync.jobs.synchost.get_plugin_settings')
    def test_is_excluded_returns_false_when_exclude_tag_empty(self, mock_settings):
        mock_settings.return_value.exclude_tag = ''
        job = SyncHostJob(instance=self.device)
        all_objects = {'tags': []}
        self.assertFalse(job._is_excluded(mock_settings.return_value, all_objects))

    @patch('nbxsync.jobs.synchost.get_plugin_settings')
    def test_is_excluded_returns_false_when_tag_not_present(self, mock_settings):
        mock_settings.return_value.exclude_tag = 'do_not_monitor'
        job = SyncHostJob(instance=self.device)
        all_objects = {'tags': []}
        self.assertFalse(job._is_excluded(mock_settings.return_value, all_objects))

    @patch('nbxsync.jobs.synchost.get_plugin_settings')
    def test_is_excluded_returns_true_when_tag_present(self, mock_settings):
        mock_settings.return_value.exclude_tag = 'do_not_monitor'
        exclude_tag = self._create_exclude_tag()
        tag_assignment = ZabbixTagAssignment.objects.create(
            zabbixtag=exclude_tag,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )
        tag_assignment._inherited_from = 'Device'

        job = SyncHostJob(instance=self.device)
        all_objects = {'tags': [tag_assignment]}
        self.assertTrue(job._is_excluded(mock_settings.return_value, all_objects))

    @patch('nbxsync.jobs.synchost.get_plugin_settings')
    @patch('nbxsync.jobs.synchost.safe_sync')
    def test_run_skips_sync_when_excluded(self, mock_safe_sync, mock_settings):
        mock_settings.return_value.exclude_tag = 'do_not_monitor'
        mock_settings.return_value.statusmapping = MagicMock()
        mock_settings.return_value.statusmapping.device = {'active': 'enabled'}
        mock_settings.return_value.statusmapping.virtualmachine = {}

        exclude_tag = self._create_exclude_tag()
        ZabbixTagAssignment.objects.create(
            zabbixtag=exclude_tag,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )

        job = SyncHostJob(instance=self.device)
        job.run()

        mock_safe_sync.assert_not_called()

    @patch('nbxsync.jobs.synchost.get_plugin_settings')
    @patch('nbxsync.jobs.synchost.safe_sync')
    @patch.object(SyncHostJob, 'verify_hostinterfaces')
    @patch.object(SyncHostJob, 'check_default_hostinterface')
    def test_run_syncs_when_not_excluded(self, mock_check, mock_verify, mock_safe_sync, mock_settings):
        mock_settings.return_value.exclude_tag = 'do_not_monitor'
        mock_settings.return_value.statusmapping = MagicMock()
        mock_settings.return_value.statusmapping.device = {'active': 'enabled'}
        mock_settings.return_value.statusmapping.virtualmachine = {}

        job = SyncHostJob(instance=self.device)
        job.run()

        mock_safe_sync.assert_called()

    @patch('nbxsync.jobs.synchost.get_plugin_settings')
    @patch('nbxsync.jobs.synchost.safe_delete')
    def test_run_deletes_host_when_excluded_and_not_already_deleted(self, mock_safe_delete, mock_settings):
        mock_settings.return_value.exclude_tag = 'do_not_monitor'
        mock_settings.return_value.statusmapping = MagicMock()
        mock_settings.return_value.statusmapping.device = {'active': 'enabled'}
        mock_settings.return_value.statusmapping.virtualmachine = {}

        exclude_tag = self._create_exclude_tag()
        ZabbixTagAssignment.objects.create(
            zabbixtag=exclude_tag,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )

        job = SyncHostJob(instance=self.device)
        job.run()

        mock_safe_delete.assert_called()

    @patch('nbxsync.jobs.synchost.get_plugin_settings')
    @patch('nbxsync.jobs.synchost.safe_delete')
    def test_run_does_not_delete_when_excluded_and_status_deleted(self, mock_safe_delete, mock_settings):
        mock_settings.return_value.exclude_tag = 'do_not_monitor'
        mock_settings.return_value.statusmapping = MagicMock()
        mock_settings.return_value.statusmapping.device = {'decommissioning': 'deleted'}
        mock_settings.return_value.statusmapping.virtualmachine = {}

        self.device.status = 'decommissioning'
        self.device.save()

        exclude_tag = self._create_exclude_tag()
        ZabbixTagAssignment.objects.create(
            zabbixtag=exclude_tag,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )

        job = SyncHostJob(instance=self.device)
        job.run()

        mock_safe_delete.assert_not_called()
