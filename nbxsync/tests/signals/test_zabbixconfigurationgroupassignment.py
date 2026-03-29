from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment
from nbxsync.signals.zabbixconfigurationgroupassignment import handle_postsave_zabbixconfigurationgroupassignment, handle_postdelete_zabbixconfigurationgroupassignment


class ZabbixConfigurationGroupAssignmentPostSaveSignalTestCase(TestCase):
    def setUp(self):
        self.cfg = ZabbixConfigurationGroup.objects.create(name='Test Config Group', description='Signal test cfg group')

    @patch('nbxsync.signals.zabbixconfigurationgroupassignment.propagate_configgroup_assignment')
    def test_postsave_enqueues_job_when_configgroup_present(self, mock_job):
        asn = ZabbixConfigurationGroupAssignment(zabbixconfigurationgroup=self.cfg, assigned_object_type=None, assigned_object_id=None)
        asn.pk = 42

        handle_postsave_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=asn, created=True)

        mock_job.delay.assert_called_once_with(42)

    @patch('nbxsync.signals.zabbixconfigurationgroupassignment.propagate_configgroup_assignment')
    def test_postsave_returns_early_when_configgroup_none(self, mock_job):
        asn = SimpleNamespace(zabbixconfigurationgroup=None)

        handle_postsave_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=asn, created=True)

        mock_job.delay.assert_not_called()

    @patch('nbxsync.signals.zabbixconfigurationgroupassignment.delete_configgroup_assignment_children')
    def test_postdelete_enqueues_job_when_configgroup_present(self, mock_job):
        asn = SimpleNamespace(zabbixconfigurationgroup=self.cfg, assigned_object_type_id=99, assigned_object_id=7)

        handle_postdelete_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=asn)

        mock_job.delay.assert_called_once_with(configgroup_pk=self.cfg.pk, assigned_object_type_pk=99, assigned_object_id=7)

    @patch('nbxsync.signals.zabbixconfigurationgroupassignment.delete_configgroup_assignment_children')
    def test_postdelete_returns_early_when_configgroup_none(self, mock_job):
        asn = SimpleNamespace(zabbixconfigurationgroup=None, assigned_object_type_id=None, assigned_object_id=None)

        handle_postdelete_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=asn)

        mock_job.delay.assert_not_called()
