from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.jobs.cfggroup import PropagateServerAssignmentJob, DeleteServerAssignmentClonesJob
from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment, ZabbixServer, ZabbixServerAssignment
from nbxsync.signals.zabbixserverassignment import handle_sync_zabbixserverassignment, handle_postdelete_zabbixserverassignment


class ZabbixServerAssignmentSignalsTestCase(TestCase):
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

    @patch('nbxsync.signals.zabbixserverassignment.propagate_server_assignment')
    def test_post_save_non_configgroup_does_not_enqueue(self, mock_job):
        assignment = ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        handle_sync_zabbixserverassignment(sender=ZabbixServerAssignment, instance=assignment)

        mock_job.delay.assert_not_called()

    @patch('nbxsync.signals.zabbixserverassignment.propagate_server_assignment')
    def test_post_save_configgroup_enqueues_job(self, mock_job):
        assignment = ZabbixServerAssignment(zabbixserver=self.server, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        assignment.pk = 999

        handle_sync_zabbixserverassignment(sender=ZabbixServerAssignment, instance=assignment)

        mock_job.delay.assert_called_once_with(assignment.pk)

    @patch('nbxsync.signals.zabbixserverassignment.delete_server_assignment_clones')
    def test_post_delete_non_configgroup_does_not_enqueue(self, mock_job):
        assignment = ZabbixServerAssignment(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        handle_postdelete_zabbixserverassignment(sender=ZabbixServerAssignment, instance=assignment)

        mock_job.delay.assert_not_called()

    @patch('nbxsync.signals.zabbixserverassignment.delete_server_assignment_clones')
    def test_post_delete_configgroup_enqueues_job(self, mock_job):
        assignment = ZabbixServerAssignment(zabbixserver=self.server, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        assignment.assigned_object_type_id = self.cfg_ct.pk
        assignment.zabbixserver_id = self.server.pk

        handle_postdelete_zabbixserverassignment(sender=ZabbixServerAssignment, instance=assignment)

        mock_job.delay.assert_called_once_with(configgroup_pk=self.cfg.pk, assigned_object_type_pk=self.cfg_ct.pk, zabbixserver_pk=self.server.pk)

    @patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda fn: fn())
    def test_propagate_job_creates_clones_for_group_members(self, _mock):
        assignment = ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        PropagateServerAssignmentJob(assignment_pk=assignment.pk).run()

        qs = ZabbixServerAssignment.objects.filter(zabbixserver=self.server)
        self.assertEqual(qs.count(), 1 + len(self.devices))
        self.assertTrue(qs.filter(assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk).exists())

        for dev in self.devices:
            self.assertTrue(qs.filter(assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg).exists(), f'Expected propagated server assignment for {dev}')

    @patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda fn: fn())
    def test_propagate_job_non_configgroup_does_not_propagate(self, _mock):
        assignment = ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        PropagateServerAssignmentJob(assignment_pk=assignment.pk).run()

        self.assertEqual(ZabbixServerAssignment.objects.filter(zabbixserver=self.server).count(), 1)

    @patch('nbxsync.jobs.cfggroup.transaction.on_commit', side_effect=lambda fn: fn())
    def test_delete_job_removes_clones(self, _mock):
        for dev in self.devices:
            ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg)

        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        self.assertEqual(ZabbixServerAssignment.objects.filter(zabbixserver=self.server).count(), 1 + len(self.devices))

        DeleteServerAssignmentClonesJob(configgroup_pk=self.cfg.pk, assigned_object_type_pk=self.cfg_ct.pk, zabbixserver_pk=self.server.pk).run()

        self.assertEqual(ZabbixServerAssignment.objects.filter(zabbixserver=self.server).count(), 1)
