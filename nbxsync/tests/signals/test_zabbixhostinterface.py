from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.test import TransactionTestCase

from utilities.testing import create_test_device

from dcim.models import Device
from ipam.models import IPAddress

from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment, ZabbixServer, ZabbixHostInterface
from nbxsync.utils.cfggroup.helpers import get_configgroup_ct_id
from nbxsync.signals.zabbixhostinterface import handle_postcreate_zabbixhostinterface, handle_postsave_zabbixhostinterface, handle_predelete_zabbixhostinterface


class ZabbixHostInterfaceSignalsTestCase(TransactionTestCase):
    def setUp(self):
        # Reset cached content type on helper if present
        if hasattr(get_configgroup_ct_id, '_ct_id'):
            delattr(get_configgroup_ct_id, '_ct_id')

        self.server = ZabbixServer.objects.create(name='CfgGroup HostInterface Server')
        self.cfg = ZabbixConfigurationGroup.objects.create(name='ConfigGroup HostInterface', description='HostInterface signal test group')

        self.devices = [
            create_test_device(name='HI Dev 1'),
            create_test_device(name='HI Dev 2'),
        ]

        # Give each device a primary IP
        for i, dev in enumerate(self.devices, start=1):
            ip = IPAddress.objects.create(address=f'10.1.{i}.1/32')
            dev.primary_ip4 = ip
            dev.save()

        self.device_ct = ContentType.objects.get_for_model(Device)
        self.cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)

    @patch('nbxsync.signals.zabbixhostinterface.transaction.on_commit', side_effect=lambda fn: fn())
    def test_postcreate_creates_children_for_members_with_primary_ip(self, *_mocks):
        dev_no_ip = create_test_device(name='HI Dev No IP')

        self.assertIsNotNone(self.devices[0].primary_ip)
        self.assertIsNone(dev_no_ip.primary_ip)

        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)
        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=dev_no_ip.pk)

        parent = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=1, useip=1, interface_type=1, ip=IPAddress.objects.create(address='10.1.100.32/32'), port=10051, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        handle_postcreate_zabbixhostinterface(sender=ZabbixHostInterface, instance=parent, created=True)

        child_with_ip = ZabbixHostInterface.objects.filter(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk, parent=parent).first()
        self.assertIsNotNone(child_with_ip)
        self.assertEqual(child_with_ip.zabbixconfigurationgroup, self.cfg)
        self.assertEqual(child_with_ip.ip, self.devices[0].primary_ip)
        self.assertEqual(child_with_ip.interface_type, parent.interface_type)
        self.assertEqual(child_with_ip.type, parent.type)
        self.assertEqual(child_with_ip.port, parent.port)
        self.assertFalse(ZabbixHostInterface.objects.filter(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=dev_no_ip.pk, parent=parent).exists())

    @patch('nbxsync.signals.zabbixhostinterface.ZabbixHostInterface.objects.filter')
    @patch('nbxsync.signals.zabbixhostinterface.ZabbixHostInterface.objects.update_or_create', side_effect=IntegrityError)
    @patch('nbxsync.signals.zabbixhostinterface.transaction.on_commit', side_effect=lambda fn: fn())
    def test_postcreate_integrity_error_falls_back_to_update(self, _mock_on_commit, mock_update_or_create, mock_filter):
        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        parent = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=1, useip=1, interface_type=1, ip=IPAddress.objects.create(address='10.1.100.21/32'), port=10051, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        qs = mock_filter.return_value

        handle_postcreate_zabbixhostinterface(sender=ZabbixHostInterface, instance=parent, created=True)

        self.assertTrue(mock_update_or_create.called)
        self.assertTrue(qs.update.called)

    def test_postcreate_returns_early_when_not_created_or_not_configgroup(self):
        hi_non_cfg = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=1, useip=1, interface_type=1, ip=IPAddress.objects.create(address='10.1.100.20/32'), port=10051, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        initial_count = ZabbixHostInterface.objects.count()

        handle_postcreate_zabbixhostinterface(sender=ZabbixHostInterface, instance=hi_non_cfg, created=False)

        self.assertEqual(ZabbixHostInterface.objects.count(), initial_count)

    @patch('nbxsync.signals.zabbixhostinterface.transaction.on_commit', side_effect=lambda fn: fn())
    def test_postsave_updates_children_with_primary_ip_only(self, *_mocks):
        ip1_initial = self.devices[0].primary_ip
        ip2_initial = self.devices[1].primary_ip

        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)
        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[1].pk)

        parent = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=1, useip=1, interface_type=1, ip=IPAddress.objects.create(address='192.0.2.30/32'), port=10051, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        handle_postcreate_zabbixhostinterface(sender=ZabbixHostInterface, instance=parent, created=True)

        child1 = ZabbixHostInterface.objects.get(parent=parent, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)
        child2 = ZabbixHostInterface.objects.get(parent=parent, assigned_object_type=self.device_ct, assigned_object_id=self.devices[1].pk)

        self.assertEqual(child1.ip, ip1_initial)
        self.assertEqual(child2.ip, ip2_initial)
        self.assertEqual(child1.port, 10051)
        self.assertEqual(child2.port, 10051)

        new_ip1 = IPAddress.objects.create(address='10.1.100.1/32')
        self.devices[0].primary_ip4 = new_ip1
        self.devices[0].save()

        self.devices[1].primary_ip4 = None
        self.devices[1].save()

        parent.port = 10052
        parent.save()

        handle_postsave_zabbixhostinterface(sender=ZabbixHostInterface, instance=parent, created=False)

        child1.refresh_from_db()
        child2.refresh_from_db()

        # Child1 must have updated IP and port
        self.assertEqual(child1.ip, new_ip1)
        self.assertEqual(child1.port, 10052)

        self.assertEqual(child2.ip, ip2_initial)
        self.assertEqual(child2.port, 10051)

    def test_postsave_returns_early_when_created_or_not_configgroup(self):
        hi_non_cfg = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=1, useip=1, interface_type=1, ip=IPAddress.objects.create(address='10.1.100.11/32'), port=10051, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        with patch('nbxsync.signals.zabbixhostinterface.transaction.on_commit') as mock_on_commit:
            handle_postsave_zabbixhostinterface(sender=ZabbixHostInterface, instance=hi_non_cfg, created=False)
            mock_on_commit.assert_not_called()

        with patch('nbxsync.signals.zabbixhostinterface.transaction.on_commit') as mock_on_commit_created:
            handle_postsave_zabbixhostinterface(sender=ZabbixHostInterface, instance=hi_non_cfg, created=True)
            mock_on_commit_created.assert_not_called()

    @patch('nbxsync.signals.zabbixhostinterface.transaction.on_commit', side_effect=lambda fn: fn())
    def test_predelete_deletes_children_for_configgroup_parent_only(self, *_mocks):
        new_dev = create_test_device(name='HI Dev Keep No CFG')

        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)
        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[1].pk)

        parent = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=1, useip=1, interface_type=1, ip=IPAddress.objects.create(address='10.1.100.5/32'), port=10051, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        child_delete = ZabbixHostInterface.objects.get(parent=parent, zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        child_keep_no_cfg = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=1, useip=1, interface_type=1, ip=IPAddress.objects.create(address='10.1.100.2/32'), port=10051, parent=parent, zabbixconfigurationgroup=None, assigned_object_type=self.device_ct, assigned_object_id=new_dev.pk)

        other_parent = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=2, useip=1, interface_type=1, ip=IPAddress.objects.create(address='10.1.100.2/32'), port=10051, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        child_keep_other_parent = ZabbixHostInterface.objects.get(parent=other_parent, zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        handle_predelete_zabbixhostinterface(sender=ZabbixHostInterface, instance=parent)

        self.assertFalse(ZabbixHostInterface.objects.filter(pk=child_delete.pk).exists())
        self.assertTrue(ZabbixHostInterface.objects.filter(pk=child_keep_no_cfg.pk).exists())
        self.assertTrue(ZabbixHostInterface.objects.filter(pk=child_keep_other_parent.pk).exists())

    def test_predelete_returns_early_when_not_configgroup_assignment(self):
        parent_non_cfg = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=1, useip=1, interface_type=1, ip=IPAddress.objects.create(address='10.1.100.9/32'), port=10051, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        child = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=2, useip=1, interface_type=1, ip=IPAddress.objects.create(address='10.1.100.10/32'), port=10051, parent=parent_non_cfg, zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        handle_predelete_zabbixhostinterface(sender=ZabbixHostInterface, instance=parent_non_cfg)

        self.assertTrue(ZabbixHostInterface.objects.filter(pk=child.pk).exists())
