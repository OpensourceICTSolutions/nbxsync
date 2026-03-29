from unittest.mock import MagicMock, patch

from django.test import TestCase

from nbxsync.choices import ZabbixProxyTypeChoices
from nbxsync.models import ZabbixProxy, ZabbixServer
from nbxsync.systemjobs.sync_proxies import SyncProxiesJob


class SyncProxiesSystemJobTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix Server 1', url='http://zabbix1.local', token='token1')
        cls.proxy1 = ZabbixProxy.objects.create(name='Proxy 1', zabbixserver=cls.server, local_address='192.168.1.1', operating_mode=ZabbixProxyTypeChoices.ACTIVE)
        cls.proxy2 = ZabbixProxy.objects.create(name='Proxy 2', zabbixserver=cls.server, local_address='192.168.1.2', operating_mode=ZabbixProxyTypeChoices.ACTIVE)

    @patch('nbxsync.systemjobs.sync_proxies.get_queue')
    def test_run_enqueues_job_for_each_proxy(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        job = SyncProxiesJob(job=MagicMock())
        job.run()

        self.assertEqual(queue.create_job.call_count, 2)
        self.assertEqual(queue.enqueue_job.call_count, 2)

        enqueued_proxies = [call.kwargs.get('args')[0] for call in queue.create_job.call_args_list]
        self.assertIn(self.proxy1, enqueued_proxies)
        self.assertIn(self.proxy2, enqueued_proxies)

    @patch('nbxsync.systemjobs.sync_proxies.get_queue')
    def test_run_passes_correct_args_to_create_job(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        job = SyncProxiesJob(job=MagicMock())
        job.run()

        for create_job_call in queue.create_job.call_args_list:
            _, kwargs = create_job_call
            self.assertEqual(kwargs.get('func'), 'nbxsync.worker.syncproxy')
            self.assertEqual(kwargs.get('timeout'), 9000)

    @patch('nbxsync.systemjobs.sync_proxies.get_queue')
    def test_run_enqueues_created_job(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        job = SyncProxiesJob(job=MagicMock())
        job.run()

        queue.enqueue_job.assert_called_with(queue.create_job.return_value)

    @patch('nbxsync.systemjobs.sync_proxies.get_queue')
    def test_run_does_nothing_when_no_zabbixservers_exist(self, mock_get_queue):
        ZabbixServer.objects.all().delete()

        job = SyncProxiesJob(job=MagicMock())
        job.run()

        mock_get_queue.assert_not_called()

    @patch('nbxsync.systemjobs.sync_proxies.get_queue')
    def test_run_does_nothing_when_server_has_no_proxies(self, mock_get_queue):
        ZabbixProxy.objects.all().delete()

        job = SyncProxiesJob(job=MagicMock())
        job.run()

        mock_get_queue.assert_not_called()
