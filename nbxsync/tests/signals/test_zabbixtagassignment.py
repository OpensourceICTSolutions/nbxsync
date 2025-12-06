from django.contrib.contenttypes.models import ContentType
from django.test import TransactionTestCase

from utilities.testing import create_test_device
from dcim.models import Device

from nbxsync.models import ZabbixTag, ZabbixTagAssignment, ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment

import nbxsync.signals.zabbixtagassignment  # noqa: F401


class ZabbixTagAssignmentSignalsTestCase(TransactionTestCase):
    def setUp(self):
        self.tag = ZabbixTag.objects.create(name='Environment', tag='env', value='{{ object.name }}')
        self.cfg = ZabbixConfigurationGroup.objects.create(name='ConfigGroup A', description='Signal test group')

        self.devices = [
            create_test_device(name='Signal Dev 1'),
            create_test_device(name='Signal Dev 2'),
        ]

        self.device_ct = ContentType.objects.get_for_model(Device)
        self.cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)

        for dev in self.devices:
            ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=dev.pk)

    def test_post_save_non_configgroup_does_not_propagate(self):
        assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        qs = ZabbixTagAssignment.objects.filter(zabbixtag=self.tag)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, assignment.pk)

    def test_post_delete_configgroup_deletes_propagated_clones(self):
        for dev in self.devices:
            ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg)

        self.assertEqual(ZabbixTagAssignment.objects.filter(zabbixtag=self.tag, zabbixconfigurationgroup=self.cfg).count(), len(self.devices))

        base = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        self.assertEqual(ZabbixTagAssignment.objects.filter(zabbixtag=self.tag).count(), 1 + len(self.devices))

        base.delete()

        self.assertEqual(ZabbixTagAssignment.objects.filter(zabbixtag=self.tag).count(), 0)
