from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.jobs.cfggroup import PropagateHostGroupAssignmentJob, DeleteHostGroupAssignmentClonesJob
from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment, ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixServer
from nbxsync.signals.zabbixhostgroupassignment import handle_postcreate_zabbixhostgroupassignment, handle_postsave_zabbixhostgroupassignment, handle_postdelete_zabbixhostgroupassignment

# Both the job's own transaction.on_commit and the helpers' need patching.
_PATCH_ON_COMMIT = [
    patch('nbxsync.jobs.cfggroup.transaction.on_commit', side_effect=lambda fn: fn()),
    patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda fn: fn()),
]


def with_on_commit(f):
    """Decorator: apply both on_commit patches to a test method."""
    for p in reversed(_PATCH_ON_COMMIT):
        f = p(f)
    return f


class ZabbixHostgroupAssignmentSignalsTestCase(TestCase):
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

    @patch('nbxsync.signals.zabbixhostgroupassignment.propagate_hostgroup_assignment')
    def test_postcreate_non_configgroup_does_not_enqueue(self, mock_job):
        assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        handle_postcreate_zabbixhostgroupassignment(sender=ZabbixHostgroupAssignment, instance=assignment, created=True)

        mock_job.delay.assert_not_called()

    @patch('nbxsync.signals.zabbixhostgroupassignment.propagate_hostgroup_assignment')
    def test_postcreate_configgroup_enqueues_job(self, mock_job):
        assignment = ZabbixHostgroupAssignment(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        assignment.pk = 999

        handle_postcreate_zabbixhostgroupassignment(sender=ZabbixHostgroupAssignment, instance=assignment, created=True)

        mock_job.delay.assert_called_once_with(assignment.pk)

    @patch('nbxsync.signals.zabbixhostgroupassignment.propagate_hostgroup_assignment')
    def test_postcreate_handler_does_not_fire_on_update(self, mock_job):
        assignment = ZabbixHostgroupAssignment(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        assignment.pk = 999

        handle_postcreate_zabbixhostgroupassignment(sender=ZabbixHostgroupAssignment, instance=assignment, created=False)

        mock_job.delay.assert_not_called()

    @patch('nbxsync.signals.zabbixhostgroupassignment.propagate_hostgroup_assignment')
    def test_postsave_non_configgroup_does_not_enqueue(self, mock_job):
        assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        handle_postsave_zabbixhostgroupassignment(sender=ZabbixHostgroupAssignment, instance=assignment, created=False)

        mock_job.delay.assert_not_called()

    @patch('nbxsync.signals.zabbixhostgroupassignment.propagate_hostgroup_assignment')
    def test_postsave_configgroup_enqueues_job(self, mock_job):
        assignment = ZabbixHostgroupAssignment(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        assignment.pk = 999

        handle_postsave_zabbixhostgroupassignment(sender=ZabbixHostgroupAssignment, instance=assignment, created=False)

        mock_job.delay.assert_called_once_with(assignment.pk)

    @patch('nbxsync.signals.zabbixhostgroupassignment.propagate_hostgroup_assignment')
    def test_postsave_handler_does_not_fire_on_create(self, mock_job):
        assignment = ZabbixHostgroupAssignment(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        assignment.pk = 999

        handle_postsave_zabbixhostgroupassignment(sender=ZabbixHostgroupAssignment, instance=assignment, created=True)

        mock_job.delay.assert_not_called()

    @patch('nbxsync.signals.zabbixhostgroupassignment.delete_hostgroup_assignment_clones')
    def test_postdelete_non_configgroup_does_not_enqueue(self, mock_job):
        assignment = ZabbixHostgroupAssignment(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        handle_postdelete_zabbixhostgroupassignment(sender=ZabbixHostgroupAssignment, instance=assignment)

        mock_job.delay.assert_not_called()

    @patch('nbxsync.signals.zabbixhostgroupassignment.delete_hostgroup_assignment_clones')
    def test_postdelete_configgroup_enqueues_job(self, mock_job):
        assignment = ZabbixHostgroupAssignment(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        assignment.assigned_object_type_id = self.cfg_ct.pk

        handle_postdelete_zabbixhostgroupassignment(sender=ZabbixHostgroupAssignment, instance=assignment)

        mock_job.delay.assert_called_once_with(configgroup_pk=self.cfg.pk)

    @with_on_commit
    def test_propagate_job_creates_clones_for_members(self, *_mocks):
        assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        PropagateHostGroupAssignmentJob(assignment_pk=assignment.pk).run()

        qs = ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup)
        self.assertEqual(qs.count(), 1 + len(self.devices))

        for dev in self.devices:
            self.assertTrue(qs.filter(assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg).exists(), f'Expected hostgroup clone for {dev}')

    @with_on_commit
    def test_propagate_job_respects_existing_null_group_assignment(self, *_mocks):
        existing = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk, zabbixconfigurationgroup=None)

        assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        PropagateHostGroupAssignmentJob(assignment_pk=assignment.pk).run()

        qs = ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup)
        self.assertEqual(qs.count(), 3)

        existing.refresh_from_db()
        self.assertIsNone(existing.zabbixconfigurationgroup)
        self.assertFalse(qs.filter(assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk, zabbixconfigurationgroup=self.cfg).exists())
        self.assertTrue(qs.filter(assigned_object_type=self.device_ct, assigned_object_id=self.devices[1].pk, zabbixconfigurationgroup=self.cfg).exists())

    @with_on_commit
    def test_propagate_job_adds_clones_for_new_members(self, *_mocks):
        ZabbixConfigurationGroupAssignment.objects.filter(zabbixconfigurationgroup=self.cfg, assigned_object_id=self.devices[1].pk).delete()

        assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        PropagateHostGroupAssignmentJob(assignment_pk=assignment.pk).run()

        self.assertEqual(ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup).count(), 2)

        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[1].pk)

        PropagateHostGroupAssignmentJob(assignment_pk=assignment.pk).run()

        qs = ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup)
        self.assertEqual(qs.count(), 3)

        for dev in self.devices:
            self.assertTrue(qs.filter(assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg).exists(), f'Expected clone for new member {dev}')

    @with_on_commit
    def test_propagate_job_non_configgroup_does_not_propagate(self, *_mocks):
        assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        PropagateHostGroupAssignmentJob(assignment_pk=assignment.pk).run()

        self.assertEqual(ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup).count(), 1)

    @with_on_commit
    def test_propagate_job_integrityerror_falls_back_to_update(self, *_mocks):
        cfg2 = ZabbixConfigurationGroup.objects.create(name='Other ConfigGroup', description='IntegrityError fallback test')

        for dev in self.devices:
            ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=cfg2)

        assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        with patch('nbxsync.jobs.cfggroup.ZabbixHostgroupAssignment.objects.update_or_create', side_effect=IntegrityError('duplicate')):
            PropagateHostGroupAssignmentJob(assignment_pk=assignment.pk).run()

        for dev in self.devices:
            a = ZabbixHostgroupAssignment.objects.get(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=dev.pk)
            self.assertEqual(a.zabbixconfigurationgroup, self.cfg, f'Expected fallback update to change group for {dev}')

    @with_on_commit
    def test_delete_job_removes_clones_for_group(self, *_mocks):
        for dev in self.devices:
            ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg)

        ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk, zabbixconfigurationgroup=self.cfg)

        self.assertEqual(ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup).count(), 1 + len(self.devices))

        DeleteHostGroupAssignmentClonesJob(configgroup_pk=self.cfg.pk).run()

        self.assertEqual(ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup).count(), 0)

    def test_delete_job_non_configgroup_does_not_delete_other_rows(self):
        for dev in self.devices:
            ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg)

        extra_dev = create_test_device(name='HGSignal Extra Dev')
        ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=extra_dev.pk)

        self.assertEqual(ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup).count(), len(self.devices) + 1)
