from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.jobs.cfggroup import PropagateTagAssignmentJob, DeleteTagAssignmentClonesJob
from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment, ZabbixTag, ZabbixTagAssignment
from nbxsync.signals.zabbixtagassignment import handle_sync_zabbixtagassignment, handle_postdelete_zabbixtagassignment


class ZabbixTagAssignmentSignalsTestCase(TestCase):
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

    @patch('nbxsync.signals.zabbixtagassignment.propagate_tag_assignment')
    def test_post_save_non_configgroup_does_not_enqueue(self, mock_job):
        assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        handle_sync_zabbixtagassignment(sender=ZabbixTagAssignment, instance=assignment)

        mock_job.delay.assert_not_called()

    @patch('nbxsync.signals.zabbixtagassignment.propagate_tag_assignment')
    def test_post_save_configgroup_enqueues_job(self, mock_job):
        assignment = ZabbixTagAssignment(zabbixtag=self.tag, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        assignment.pk = 999

        handle_sync_zabbixtagassignment(sender=ZabbixTagAssignment, instance=assignment)

        mock_job.delay.assert_called_once_with(assignment.pk)

    @patch('nbxsync.signals.zabbixtagassignment.delete_tag_assignment_clones')
    def test_post_delete_non_configgroup_does_not_enqueue(self, mock_job):
        assignment = ZabbixTagAssignment(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        handle_postdelete_zabbixtagassignment(sender=ZabbixTagAssignment, instance=assignment)

        mock_job.delay.assert_not_called()

    @patch('nbxsync.signals.zabbixtagassignment.delete_tag_assignment_clones')
    def test_post_delete_configgroup_enqueues_job(self, mock_job):
        assignment = ZabbixTagAssignment(zabbixtag=self.tag, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        assignment.assigned_object_type_id = self.cfg_ct.pk
        assignment.zabbixtag_id = self.tag.pk

        handle_postdelete_zabbixtagassignment(sender=ZabbixTagAssignment, instance=assignment)

        mock_job.delay.assert_called_once_with(configgroup_pk=self.cfg.pk, zabbixtag_pk=self.tag.pk)

    @patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda fn: fn())
    def test_propagate_job_creates_clones_for_group_members(self, _mock):
        assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        PropagateTagAssignmentJob(assignment_pk=assignment.pk).run()

        qs = ZabbixTagAssignment.objects.filter(zabbixtag=self.tag)
        self.assertEqual(qs.count(), 1 + len(self.devices))

        for dev in self.devices:
            self.assertTrue(
                qs.filter(assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg).exists(),
                f'Expected propagated tag assignment for {dev}',
            )

    @patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda fn: fn())
    def test_propagate_job_non_configgroup_does_not_propagate(self, _mock):
        assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        PropagateTagAssignmentJob(assignment_pk=assignment.pk).run()

        self.assertEqual(ZabbixTagAssignment.objects.filter(zabbixtag=self.tag).count(), 1)

    @patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda fn: fn())
    @patch('nbxsync.jobs.cfggroup.transaction.on_commit', side_effect=lambda fn: fn())
    def test_delete_job_removes_clones(self, *_mocks):
        base = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        PropagateTagAssignmentJob(assignment_pk=base.pk).run()

        self.assertEqual(ZabbixTagAssignment.objects.filter(zabbixtag=self.tag).count(), 1 + len(self.devices))

        DeleteTagAssignmentClonesJob(configgroup_pk=self.cfg.pk, zabbixtag_pk=self.tag.pk).run()

        self.assertEqual(ZabbixTagAssignment.objects.filter(zabbixtag=self.tag).count(), 1)
