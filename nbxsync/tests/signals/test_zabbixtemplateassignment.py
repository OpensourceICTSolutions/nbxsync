from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.jobs.cfggroup import PropagateTemplateAssignmentJob, DeleteTemplateAssignmentClonesJob
from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment, ZabbixServer, ZabbixTemplate, ZabbixTemplateAssignment
from nbxsync.signals.zabbixtemplateassignment import handle_postsave_zabbixtemplateassignment, handle_postdelete_zabbixtemplateassignment


class ZabbixTemplateAssignmentSignalsTestCase(TestCase):
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

    @patch('nbxsync.signals.zabbixtemplateassignment.propagate_template_assignment')
    def test_postsave_non_configgroup_does_not_enqueue(self, mock_job):
        assignment = ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        handle_postsave_zabbixtemplateassignment(sender=ZabbixTemplateAssignment, instance=assignment)

        mock_job.delay.assert_not_called()

    @patch('nbxsync.signals.zabbixtemplateassignment.propagate_template_assignment')
    def test_postsave_configgroup_enqueues_job(self, mock_job):
        assignment = ZabbixTemplateAssignment(zabbixtemplate=self.template, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        assignment.pk = 999

        handle_postsave_zabbixtemplateassignment(sender=ZabbixTemplateAssignment, instance=assignment)

        mock_job.delay.assert_called_once_with(assignment.pk)

    @patch('nbxsync.signals.zabbixtemplateassignment.delete_template_assignment_clones')
    def test_postdelete_non_configgroup_does_not_enqueue(self, mock_job):
        assignment = ZabbixTemplateAssignment(zabbixtemplate=self.template, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        handle_postdelete_zabbixtemplateassignment(sender=ZabbixTemplateAssignment, instance=assignment)

        mock_job.delay.assert_not_called()

    @patch('nbxsync.signals.zabbixtemplateassignment.delete_template_assignment_clones')
    def test_postdelete_configgroup_enqueues_job(self, mock_job):
        assignment = ZabbixTemplateAssignment(zabbixtemplate=self.template, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        assignment.assigned_object_type_id = self.cfg_ct.pk
        assignment.zabbixtemplate_id = self.template.pk

        handle_postdelete_zabbixtemplateassignment(sender=ZabbixTemplateAssignment, instance=assignment)

        mock_job.delay.assert_called_once_with(configgroup_pk=self.cfg.pk, assigned_object_type_pk=self.cfg_ct.pk, zabbixtemplate_pk=self.template.pk)

    @patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda fn: fn())
    def test_propagate_job_creates_clones_for_group_members(self, _mock):
        assignment = ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        PropagateTemplateAssignmentJob(assignment_pk=assignment.pk).run()

        qs = ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template)
        self.assertEqual(qs.count(), 1 + len(self.devices))
        self.assertTrue(qs.filter(assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk).exists())

        for dev in self.devices:
            self.assertTrue(qs.filter(zabbixtemplate=self.template, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg).exists(), f'Expected propagated template assignment for {dev}')

    @patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda fn: fn())
    def test_propagate_job_non_configgroup_does_not_propagate(self, _mock):
        assignment = ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        PropagateTemplateAssignmentJob(assignment_pk=assignment.pk).run()

        self.assertEqual(ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template).count(), 1)

    @patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda fn: fn())
    @patch('nbxsync.jobs.cfggroup.transaction.on_commit', side_effect=lambda fn: fn())
    def test_delete_job_removes_clones(self, *_mocks):
        base = ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        PropagateTemplateAssignmentJob(assignment_pk=base.pk).run()

        self.assertEqual(ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template).count(), 1 + len(self.devices))

        DeleteTemplateAssignmentClonesJob(configgroup_pk=self.cfg.pk, assigned_object_type_pk=self.cfg_ct.pk, zabbixtemplate_pk=self.template.pk).run()

        self.assertEqual(ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template).count(), 1)

    def test_delete_job_non_configgroup_is_a_noop(self):
        for dev in self.devices:
            ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg)

        extra_dev = create_test_device(name='TplSignal Extra Dev')
        ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.device_ct, assigned_object_id=extra_dev.pk)

        count_before = ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template).count()
        self.assertEqual(count_before, len(self.devices) + 1)
