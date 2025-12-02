from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment
from nbxsync.signals.zabbixconfigurationgroupassignment import handle_postsave_zabbixconfigurationgroupassignment, handle_postdelete_zabbixconfigurationgroupassignment


class ZabbixConfigurationGroupAssignmentPostSaveSignalTestCase(TestCase):
    def setUp(self):
        self.cfg = ZabbixConfigurationGroup.objects.create(name='Test Config Group', description='Signal test cfg group')

    @patch('nbxsync.signals.zabbixconfigurationgroupassignment.resync_zabbixconfigurationgroupassignment')
    def test_postsave_calls_resync_when_configgroup_present(self, mock_resync):
        asn = ZabbixConfigurationGroupAssignment(zabbixconfigurationgroup=self.cfg, assigned_object_type=None, assigned_object_id=None)

        handle_postsave_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=asn, created=True)

        mock_resync.assert_called_once_with(asn)

    @patch('nbxsync.signals.zabbixconfigurationgroupassignment.resync_zabbixconfigurationgroupassignment')
    def test_postsave_returns_early_when_configgroup_none(self, mock_resync):
        assignment = SimpleNamespace(zabbixconfigurationgroup=None)

        handle_postsave_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=assignment, created=True)

        # No resync call when configgroup is None
        mock_resync.assert_not_called()

    @patch('nbxsync.signals.zabbixconfigurationgroupassignment.transaction.on_commit')
    def test_postdelete_returns_early_when_configgroup_none(self, mock_on_commit):
        assignment = SimpleNamespace(zabbixconfigurationgroup=None, assigned_object_type=None, assigned_object_id=None)

        handle_postdelete_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=assignment)

        # No on_commit scheduled when configgroup is None
        mock_on_commit.assert_not_called()
