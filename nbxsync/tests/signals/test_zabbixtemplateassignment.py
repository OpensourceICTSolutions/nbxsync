from django.contrib.contenttypes.models import ContentType
from django.test import TransactionTestCase

from utilities.testing import create_test_device
from dcim.models import Device

from nbxsync.models import ZabbixServer, ZabbixTemplate, ZabbixTemplateAssignment, ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment

import nbxsync.signals.zabbixtemplateassignment  # noqa: F401


class ZabbixTemplateAssignmentSignalsTestCase(TransactionTestCase):
    def setUp(self):
        self.server = ZabbixServer.objects.create(name='Template Signal Server')
        self.template = ZabbixTemplate.objects.create(name='Template Signals', templateid=1001, zabbixserver=self.server)
        self.cfg = ZabbixConfigurationGroup.objects.create(name='ConfigGroup Template Signals', description='Template assignment signal test group')

        self.devices = [
            create_test_device(name='TplSignal Dev 1'),
            create_test_device(name='TplSignal Dev 2'),
        ]

        self.device_ct = ContentType.objects.get_for_model(Device)
        self.cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)

        for dev in self.devices:
            ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=dev.pk)

    def test_postsave_non_configgroup_does_not_propagate(self):
        base = ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        qs = ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, base.pk)

    def test_postsave_configgroup_propagates_to_group_members(self):
        ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        qs = ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template)

        self.assertEqual(qs.count(), 1 + len(self.devices))
        self.assertTrue(qs.filter(assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk).exists())

        for dev in self.devices:
            self.assertTrue(qs.filter(zabbixtemplate=self.template, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg).exists(), f'Expected propagated template assignment for {dev}')

    def test_postdelete_non_configgroup_does_not_delete_group_clones(self):
        for dev in self.devices:
            ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg)

        extra_dev = create_test_device(name='TplSignal Extra Dev')
        non_cfg = ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.device_ct, assigned_object_id=extra_dev.pk)

        self.assertEqual(ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template).count(), len(self.devices) + 1)

        non_cfg.delete()

        self.assertEqual(ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template).count(), len(self.devices))

    def test_postdelete_configgroup_deletes_clones_for_group(self):
        base = ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        self.assertEqual(ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template).count(), 1 + len(self.devices))

        base.delete()

        self.assertEqual(ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template).count(), 0)
