from django.contrib.contenttypes.models import ContentType
from django.test import TransactionTestCase

from utilities.testing import create_test_device
from dcim.models import Device

from nbxsync.models import ZabbixServer, ZabbixServerAssignment, ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment

import nbxsync.signals.zabbixserverassignment  # noqa: F401


class ZabbixServerAssignmentSignalsTestCase(TransactionTestCase):
    def setUp(self):
        self.server = ZabbixServer.objects.create(name='Signal Test Server', description='Server for signal tests', url='http://signals.example.com', token='signal-token', validate_certs=True)
        self.cfg = ZabbixConfigurationGroup.objects.create(name='ConfigGroup Server Signals', description='Server assignment signal test group')

        self.devices = [
            create_test_device(name='ServerSignal Dev 1'),
            create_test_device(name='ServerSignal Dev 2'),
        ]

        self.device_ct = ContentType.objects.get_for_model(Device)
        self.cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)

        for dev in self.devices:
            ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=dev.pk)

    def test_post_save_non_configgroup_does_not_propagate(self):
        assignment = ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        qs = ZabbixServerAssignment.objects.filter(zabbixserver=self.server)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, assignment.pk)

    def test_post_save_configgroup_propagates_to_group_members(self):
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        qs = ZabbixServerAssignment.objects.filter(zabbixserver=self.server)
        self.assertEqual(qs.count(), 1 + len(self.devices))
        self.assertTrue(qs.filter(assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk).exists())

        for dev in self.devices:
            self.assertTrue(qs.filter(assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg).exists(), f'Expected propagated server assignment for {dev}')

    def test_post_delete_configgroup_deletes_propagated_clones(self):
        for dev in self.devices:
            ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg)

        self.assertEqual(ZabbixServerAssignment.objects.filter(zabbixserver=self.server, zabbixconfigurationgroup=self.cfg).count(), len(self.devices))

        base = ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        self.assertEqual(ZabbixServerAssignment.objects.filter(zabbixserver=self.server).count(), 1 + len(self.devices))

        base.delete()

        self.assertEqual(ZabbixServerAssignment.objects.filter(zabbixserver=self.server).count(), 0)
