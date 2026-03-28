from unittest.mock import MagicMock, call, patch

from django.test import TestCase

from nbxsync.models import ZabbixServer
from nbxsync.systemjobs.sync_templates import SyncTemplatesJob


class SyncTemplatesSystemJobTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server1 = ZabbixServer.objects.create(name='Zabbix Server 1', url='http://zabbix1.local', token='token1')
        cls.server2 = ZabbixServer.objects.create(name='Zabbix Server 2', url='http://zabbix2.local', token='token2')

    @patch('nbxsync.systemjobs.sync_templates.get_queue')
    def test_run_enqueues_job_for_each_zabbixserver(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        job = SyncTemplatesJob(job=MagicMock())
        job.run()

        self.assertEqual(mock_get_queue.call_count, ZabbixServer.objects.count())
        mock_get_queue.assert_called_with('low')

        self.assertEqual(queue.create_job.call_count, ZabbixServer.objects.count())
        self.assertEqual(queue.enqueue_job.call_count, ZabbixServer.objects.count())

    @patch('nbxsync.systemjobs.sync_templates.get_queue')
    def test_run_passes_correct_args_to_create_job(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        job = SyncTemplatesJob(job=MagicMock())
        job.run()

        for create_job_call in queue.create_job.call_args_list:
            _, kwargs = create_job_call
            self.assertEqual(kwargs.get('func'), 'nbxsync.worker.synctemplates')
            self.assertEqual(kwargs.get('timeout'), 9000)
            self.assertIn(kwargs.get('args')[0], [self.server1, self.server2])

    @patch('nbxsync.systemjobs.sync_templates.get_queue')
    def test_run_enqueues_created_job(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        job = SyncTemplatesJob(job=MagicMock())
        job.run()

        queue.enqueue_job.assert_called_with(queue.create_job.return_value)

    @patch('nbxsync.systemjobs.sync_templates.get_queue')
    def test_run_does_nothing_when_no_zabbixservers_exist(self, mock_get_queue):
        ZabbixServer.objects.all().delete()

        job = SyncTemplatesJob(job=MagicMock())
        job.run()

        mock_get_queue.assert_not_called()
