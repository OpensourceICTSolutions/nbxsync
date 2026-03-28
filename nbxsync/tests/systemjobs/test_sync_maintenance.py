from unittest.mock import MagicMock, patch

from django.test import TestCase

from nbxsync.models import ZabbixMaintenance, ZabbixServer
from nbxsync.systemjobs.sync_maintenance import SyncMaintenanceJob


class SyncMaintenanceSystemJobTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix Server 1', url='http://zabbix1.local', token='token1')
        cls.mw1 = ZabbixMaintenance.objects.create(name='MW 1', zabbixserver=cls.server, active_since='2024-01-01 00:00:00', active_till='2024-01-02 00:00:00')
        cls.mw2 = ZabbixMaintenance.objects.create(name='MW 2', zabbixserver=cls.server, active_since='2024-01-01 00:00:00', active_till='2024-01-02 00:00:00')

    @patch('nbxsync.systemjobs.sync_maintenance.get_queue')
    @patch('nbxsync.systemjobs.sync_maintenance.get_maintenance_can_sync', return_value=True)
    def test_run_enqueues_job_for_each_syncable_maintenance(self, mock_can_sync, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        job = SyncMaintenanceJob(job=MagicMock())
        job.run()

        self.assertEqual(queue.create_job.call_count, 2)
        self.assertEqual(queue.enqueue_job.call_count, 2)

        enqueued_mws = [call.kwargs.get('args', call.args[1] if len(call.args) > 1 else None)[0] for call in queue.create_job.call_args_list]
        self.assertIn(self.mw1, enqueued_mws)
        self.assertIn(self.mw2, enqueued_mws)

    @patch('nbxsync.systemjobs.sync_maintenance.get_queue')
    @patch('nbxsync.systemjobs.sync_maintenance.get_maintenance_can_sync', return_value=True)
    def test_run_passes_correct_args_to_create_job(self, mock_can_sync, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        job = SyncMaintenanceJob(job=MagicMock())
        job.run()

        for create_job_call in queue.create_job.call_args_list:
            _, kwargs = create_job_call
            self.assertEqual(kwargs.get('func'), 'nbxsync.worker.syncmaintenance')
            self.assertEqual(kwargs.get('timeout'), 9000)

    @patch('nbxsync.systemjobs.sync_maintenance.get_queue')
    @patch('nbxsync.systemjobs.sync_maintenance.get_maintenance_can_sync', return_value=False)
    def test_run_skips_maintenance_when_cannot_sync(self, mock_can_sync, mock_get_queue):
        job = SyncMaintenanceJob(job=MagicMock())
        job.run()

        mock_get_queue.assert_not_called()

    @patch('nbxsync.systemjobs.sync_maintenance.get_queue')
    @patch('nbxsync.systemjobs.sync_maintenance.get_maintenance_can_sync')
    def test_run_only_enqueues_syncable_maintenance(self, mock_can_sync, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        # mw1 can sync, mw2 cannot
        mock_can_sync.side_effect = lambda mw: mw == self.mw1

        job = SyncMaintenanceJob(job=MagicMock())
        job.run()

        self.assertEqual(queue.create_job.call_count, 1)
        enqueued_mw = queue.create_job.call_args.kwargs.get('args')[0]
        self.assertEqual(enqueued_mw, self.mw1)

    @patch('nbxsync.systemjobs.sync_maintenance.get_queue')
    @patch('nbxsync.systemjobs.sync_maintenance.get_maintenance_can_sync', return_value=True)
    def test_run_does_nothing_when_no_zabbixservers_exist(self, mock_can_sync, mock_get_queue):
        ZabbixServer.objects.all().delete()

        job = SyncMaintenanceJob(job=MagicMock())
        job.run()

        mock_get_queue.assert_not_called()
