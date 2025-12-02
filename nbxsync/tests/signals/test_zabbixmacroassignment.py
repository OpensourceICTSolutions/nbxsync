from django.contrib.contenttypes.models import ContentType
from django.test import TransactionTestCase

from utilities.testing import create_test_device
from dcim.models import Device

from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment, ZabbixMacro, ZabbixMacroAssignment

import nbxsync.signals.zabbixmacroassignment  # noqa: F401


class ZabbixMacroAssignmentSignalsTestCase(TransactionTestCase):
    def setUp(self):
        self.cfg = ZabbixConfigurationGroup.objects.create(name='ConfigGroup Macro Signals', description='Macro assignment signal test group')

        self.devices = [
            create_test_device(name='MacroSignal Dev 1'),
            create_test_device(name='MacroSignal Dev 2'),
        ]

        self.device_ct = ContentType.objects.get_for_model(Device)
        self.cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)

        for dev in self.devices:
            ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=dev.pk)

        self.macro = ZabbixMacro.objects.create(macro='{$TEST}', value='initial', description='Macro for signal tests', type='hg')

    def test_postcreate_non_configgroup_does_not_propagate(self):
        base = ZabbixMacroAssignment.objects.create(zabbixmacro=self.macro, is_regex=False, context='', value='device-only', assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        qs = ZabbixMacroAssignment.objects.filter(zabbixmacro=self.macro)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, base.pk)

    def test_postcreate_configgroup_propagates_to_group_members(self):
        base = ZabbixMacroAssignment.objects.create(zabbixmacro=self.macro, is_regex=True, context='cfg-context', value='cfg-value', assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        qs = ZabbixMacroAssignment.objects.filter(zabbixmacro=self.macro)

        self.assertEqual(qs.count(), 1 + len(self.devices))
        self.assertTrue(qs.filter(assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk, parent__isnull=True).exists())

        for dev in self.devices:
            child = ZabbixMacroAssignment.objects.get(
                assigned_object_type=self.device_ct,
                assigned_object_id=dev.pk,
            )
            self.assertEqual(child.zabbixmacro, base.zabbixmacro)
            self.assertEqual(child.is_regex, base.is_regex)
            self.assertEqual(child.context, base.context)
            self.assertEqual(child.value, base.value)
            self.assertEqual(child.parent, base)
            self.assertEqual(child.zabbixconfigurationgroup, self.cfg)

    def test_postsave_updates_children_with_non_null_group_only(self):
        base = ZabbixMacroAssignment.objects.create(zabbixmacro=self.macro, is_regex=False, context='old-context', value='old-value', assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        special_child = ZabbixMacroAssignment.objects.get(zabbixmacro=self.macro, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)
        special_child.context = 'special-context'
        special_child.value = 'special-value'
        special_child.zabbixconfigurationgroup = None
        special_child.save()

        base.is_regex = True
        base.context = 'new-context'
        base.value = 'new-value'
        base.save()

        for dev in self.devices:
            if dev == self.devices[0]:
                continue

            child = ZabbixMacroAssignment.objects.get(zabbixmacro=self.macro, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, parent=base, zabbixconfigurationgroup=self.cfg)
            self.assertTrue(child.is_regex)
            self.assertEqual(child.context, 'new-context')
            self.assertEqual(child.value, 'new-value')

        special_child.refresh_from_db()
        self.assertFalse(special_child.is_regex)
        self.assertEqual(special_child.context, 'special-context')
        self.assertEqual(special_child.value, 'special-value')
        self.assertIsNone(special_child.zabbixconfigurationgroup)

    def test_postsave_non_configgroup_does_not_update_other_rows(self):
        base = ZabbixMacroAssignment.objects.create(zabbixmacro=self.macro, is_regex=False, context='orig', value='orig', assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        base.context = 'changed'
        base.value = 'changed'
        base.save()

        qs = ZabbixMacroAssignment.objects.filter(zabbixmacro=self.macro)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, base.pk)
        self.assertEqual(qs.first().context, 'changed')
        self.assertEqual(qs.first().value, 'changed')

    def test_predelete_non_configgroup_does_not_delete_others(self):
        base_cfg = ZabbixMacroAssignment.objects.create(zabbixmacro=self.macro, is_regex=False, context='cfg', value='cfg', assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        cfg_related_count = ZabbixMacroAssignment.objects.filter(parent=base_cfg).count()
        self.assertEqual(cfg_related_count, len(self.devices))

        non_cfg = ZabbixMacroAssignment.objects.create(zabbixmacro=self.macro, is_regex=False, context='device-only', value='device-only', assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        total_before = ZabbixMacroAssignment.objects.filter(zabbixmacro=self.macro).count()

        non_cfg.delete()

        total_after = ZabbixMacroAssignment.objects.filter(zabbixmacro=self.macro).count()

        self.assertEqual(total_before - 1, total_after)
        self.assertEqual(ZabbixMacroAssignment.objects.filter(parent=base_cfg).count(), len(self.devices))

    def test_predelete_configgroup_deletes_children_for_that_group(self):
        base = ZabbixMacroAssignment.objects.create(zabbixmacro=self.macro, is_regex=False, context='cfg-parent', value='cfg-parent', assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        self.assertEqual(ZabbixMacroAssignment.objects.filter(parent=base, zabbixconfigurationgroup=self.cfg).count(), len(self.devices))

        base.delete()

        self.assertEqual(ZabbixMacroAssignment.objects.filter(zabbixconfigurationgroup=self.cfg).count(), 0)
