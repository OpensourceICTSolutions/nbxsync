from django.contrib.contenttypes.models import ContentType
from django.test import TransactionTestCase
from django.db import IntegrityError
from unittest.mock import patch

from utilities.testing import create_test_device
from dcim.models import Device

from nbxsync.models import ZabbixServer, ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment

# Ensure signal handlers are imported and registered
import nbxsync.signals.zabbixhostgroupassignment  # noqa: F401


class ZabbixHostgroupAssignmentSignalsTestCase(TransactionTestCase):
    def setUp(self):
        self.server = ZabbixServer.objects.create(name='Signal Test Server')
        self.hostgroup = ZabbixHostgroup.objects.create(name='HG Signals', value='hg-signals', zabbixserver=self.server)
        self.cfg = ZabbixConfigurationGroup.objects.create(name='ConfigGroup HG Signals', description='Hostgroup assignment signal test group')

        self.devices = [
            create_test_device(name='HGSignal Dev 1'),
            create_test_device(name='HGSignal Dev 2'),
        ]

        self.device_ct = ContentType.objects.get_for_model(Device)
        self.cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)

        for dev in self.devices:
            ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=dev.pk)

    def test_postcreate_non_configgroup_does_not_create_clones(self):
        base = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        qs = ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, base.pk)

    def test_postcreate_configgroup_creates_clones_for_members(self):
        ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        qs = ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup)

        self.assertEqual(qs.count(), 1 + len(self.devices))
        self.assertTrue(qs.filter(assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk).exists())

        for dev in self.devices:
            self.assertTrue(qs.filter(assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg).exists(), f'Expected hostgroup clone for {dev}')

    def test_postcreate_respects_existing_null_group_assignment(self):
        existing = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk, zabbixconfigurationgroup=None)

        ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        qs = ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup)

        self.assertEqual(qs.count(), 3)

        existing.refresh_from_db()

        self.assertIsNone(existing.zabbixconfigurationgroup)
        self.assertFalse(qs.filter(assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk, zabbixconfigurationgroup=self.cfg).exists())
        self.assertTrue(qs.filter(assigned_object_type=self.device_ct, assigned_object_id=self.devices[1].pk, zabbixconfigurationgroup=self.cfg).exists())

    def test_postsave_configgroup_adds_clones_for_new_members(self):
        ZabbixConfigurationGroupAssignment.objects.filter(zabbixconfigurationgroup=self.cfg, assigned_object_id=self.devices[1].pk).delete()

        base = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        qs_initial = ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup)
        self.assertEqual(qs_initial.count(), 2)

        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[1].pk)

        base.refresh_from_db()
        base.save()

        qs = ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup)

        self.assertEqual(qs.count(), 3)

        for dev in self.devices:
            self.assertTrue(
                qs.filter(assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg).exists(),
                f'Expected clone for new member {dev}',
            )

    def test_postsave_non_configgroup_does_not_create_clones(self):
        base = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        base.save()

        qs = ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup)
        self.assertEqual(qs.count(), 1)

    def test_postdelete_non_configgroup_does_not_delete_clones(self):
        for dev in self.devices:
            ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg)

        extra_dev = create_test_device(name='HGSignal Extra Dev')
        non_cfg = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=extra_dev.pk)

        self.assertEqual(ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup).count(), len(self.devices) + 1)

        non_cfg.delete()

        self.assertEqual(ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup).count(), len(self.devices))

    def test_postdelete_configgroup_deletes_clones_for_group(self):
        for dev in self.devices:
            ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg)

        base = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk, zabbixconfigurationgroup=self.cfg)

        self.assertEqual(ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup).count(), 1 + len(self.devices))

        base.delete()

        self.assertEqual(ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup).count(), 0)

    def test_postsave_respects_existing_null_group_assignment(self):
        base = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        device0_assignment = ZabbixHostgroupAssignment.objects.get(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)
        device0_assignment.zabbixconfigurationgroup = None
        device0_assignment.save()

        device1_assignmnet = ZabbixHostgroupAssignment.objects.get(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.devices[1].pk)
        self.assertIsNone(device0_assignment.zabbixconfigurationgroup)
        self.assertEqual(device1_assignmnet.zabbixconfigurationgroup, self.cfg)

        base.refresh_from_db()
        base.save()

        device0_assignment.refresh_from_db()
        self.assertIsNone(device0_assignment.zabbixconfigurationgroup)

        self.assertEqual(ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk).count(), 1)

    def test_postcreate_integrityerror_falls_back_to_update(self):
        cfg2 = ZabbixConfigurationGroup.objects.create(name='Other ConfigGroup', description='Used to test IntegrityError fallback (create)')

        for dev in self.devices:
            ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=cfg2)

        with patch('nbxsync.signals.zabbixhostgroupassignment.ZabbixHostgroupAssignment.objects.update_or_create', side_effect=IntegrityError('duplicate')):
            ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        for dev in self.devices:
            assignment = ZabbixHostgroupAssignment.objects.get(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=dev.pk)
            self.assertEqual(assignment.zabbixconfigurationgroup, self.cfg, f'Expected fallback update to change group for {dev}')

    def test_postsave_integrityerror_falls_back_to_update(self):
        base = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        cfg2 = ZabbixConfigurationGroup.objects.create(name='Other ConfigGroup (update)', description='Used to test IntegrityError fallback (update)')

        for dev in self.devices:
            assignment = ZabbixHostgroupAssignment.objects.get(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=dev.pk)
            assignment.zabbixconfigurationgroup = cfg2
            assignment.save()

        for dev in self.devices:
            assignment = ZabbixHostgroupAssignment.objects.get(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=dev.pk)
            self.assertEqual(assignment.zabbixconfigurationgroup, cfg2)

        with patch('nbxsync.signals.zabbixhostgroupassignment.ZabbixHostgroupAssignment.objects.update_or_create', side_effect=IntegrityError('duplicate')):
            base.refresh_from_db()
            base.save()

        for dev in self.devices:
            assignment = ZabbixHostgroupAssignment.objects.get(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=dev.pk)
            self.assertEqual(assignment.zabbixconfigurationgroup, self.cfg, f'Expected fallback update to change group for {dev}')
