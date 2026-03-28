from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.choices import ZabbixProxyTypeChoices, ZabbixTLSChoices
from nbxsync.jobs.deletehost import DeleteHostJob
from nbxsync.models import ZabbixProxy, ZabbixProxyGroup, ZabbixServer, ZabbixServerAssignment
from nbxsync.utils.sync import HostSync


class DeleteHostJobTestCase(TestCase):
    def setUp(self):
        self.device = create_test_device(name='DeleteHostVM')
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

        self.zabbixserverassignment = ZabbixServerAssignment.objects.create(zabbixserver=self.zabbixserver, assigned_object_type=self.device_ct, assigned_object_id=self.device.id, hostid='12345', zabbixproxy=self.proxy)

    @patch('nbxsync.jobs.deletehost.safe_delete')
    def test_run_calls_delete_host_for_each_assignment(self, mock_safe_delete):
        job = DeleteHostJob(instance=self.device)
        job.run()

        mock_safe_delete.assert_called_once_with(HostSync, self.zabbixserverassignment)

    @patch('nbxsync.jobs.deletehost.safe_delete')
    def test_run_skips_when_assignment_sync_disabled(self, mock_safe_delete):
        self.zabbixserverassignment.sync_enabled = False
        self.zabbixserverassignment.save()

        job = DeleteHostJob(instance=self.device)
        job.run()

        mock_safe_delete.assert_not_called()

    @patch('nbxsync.jobs.deletehost.safe_delete')
    def test_run_skips_when_zabbixserver_sync_disabled(self, mock_safe_delete):
        self.zabbixserver.sync_enabled = False
        self.zabbixserver.save()

        job = DeleteHostJob(instance=self.device)
        job.run()

        mock_safe_delete.assert_not_called()

    @patch('nbxsync.jobs.deletehost.safe_delete')
    def test_run_skips_when_both_assignment_and_zabbixserver_sync_disabled(self, mock_safe_delete):
        self.zabbixserverassignment.sync_enabled = False
        self.zabbixserverassignment.save()
        self.zabbixserver.sync_enabled = False
        self.zabbixserver.save()

        job = DeleteHostJob(instance=self.device)
        job.run()

        mock_safe_delete.assert_not_called()

    @patch('nbxsync.jobs.deletehost.safe_delete')
    def test_run_does_nothing_when_no_assignments_exist(self, mock_safe_delete):
        ZabbixServerAssignment.objects.all().delete()

        job = DeleteHostJob(instance=self.device)
        job.run()

        mock_safe_delete.assert_not_called()
