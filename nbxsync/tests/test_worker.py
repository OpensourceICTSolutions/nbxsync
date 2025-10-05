from unittest.mock import MagicMock, patch

from django.test import TestCase

from nbxsync.models import ZabbixServer
from nbxsync.worker import synchost, syncproxy, syncproxygroup, synctemplates


class RQJobTests(TestCase):
    def setUp(self):
        self.instance = ZabbixServer.objects.create(name='Test Server', url='http://example.com', token='abc123', validate_certs=True)

    @patch('nbxsync.worker.SyncHostJob')
    def test_synchost_runs_job(self, mock_job_class):
        mock_job = MagicMock()
        mock_job_class.return_value = mock_job

        synchost(self.instance)

        mock_job_class.assert_called_once_with(instance=self.instance)
        mock_job.run.assert_called_once()

    @patch('nbxsync.worker.SyncProxyGroupJob')
    def test_syncproxygroup_runs_job(self, mock_job_class):
        mock_job = MagicMock()
        mock_job_class.return_value = mock_job

        syncproxygroup(self.instance)

        mock_job_class.assert_called_once_with(instance=self.instance)
        mock_job.run.assert_called_once()

    @patch('nbxsync.worker.SyncProxyJob')
    def test_syncproxy_runs_job(self, mock_job_class):
        mock_job = MagicMock()
        mock_job_class.return_value = mock_job

        syncproxy(self.instance)

        mock_job_class.assert_called_once_with(instance=self.instance)
        mock_job.run.assert_called_once()

    @patch('nbxsync.worker.SyncTemplatesJob')
    def test_synctemplates_runs_job(self, mock_job_class):
        mock_job = MagicMock()
        mock_job_class.return_value = mock_job

        synctemplates(self.instance)

        mock_job_class.assert_called_once_with(instance=self.instance)
        mock_job.run.assert_called_once()
