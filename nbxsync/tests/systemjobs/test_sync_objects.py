from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.models import ZabbixConfigurationGroup, ZabbixServer, ZabbixServerAssignment
from nbxsync.systemjobs.sync_objects import SyncObjectsJob


class SyncObjectsSystemJobTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix Server 1', url='http://zabbix1.local', token='token1')
        cls.device1 = create_test_device(name='SyncObjects Dev 1')
        cls.device2 = create_test_device(name='SyncObjects Dev 2')
        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_enqueues_job_for_each_device(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.device1.pk)
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.device2.pk)

        job = SyncObjectsJob(job=MagicMock())
        job.run()

        self.assertEqual(queue.create_job.call_count, 2)
        self.assertEqual(queue.enqueue_job.call_count, 2)

        enqueued_instances = [call.kwargs.get('args')[0] for call in queue.create_job.call_args_list]
        self.assertIn(self.device1, enqueued_instances)
        self.assertIn(self.device2, enqueued_instances)

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_passes_correct_args_to_create_job(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.device1.pk)

        job = SyncObjectsJob(job=MagicMock())
        job.run()

        _, kwargs = queue.create_job.call_args
        self.assertEqual(kwargs.get('func'), 'nbxsync.worker.synchost')
        self.assertEqual(kwargs.get('timeout'), 9000)
        self.assertEqual(kwargs.get('args')[0], self.device1)

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_skips_configurationgroup_assignments(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        cfg = ZabbixConfigurationGroup.objects.create(name='Test CFG', description='')
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.cfg_ct, assigned_object_id=cfg.pk)

        job = SyncObjectsJob(job=MagicMock())
        job.run()

        mock_get_queue.assert_not_called()

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_stops_entirely_on_duplicate_assigned_object(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        device3 = create_test_device(name='SyncObjects Dev 3')

        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.device1.pk)
        # Second assignment for device1 triggers the `return`
        server2 = ZabbixServer.objects.create(name='Zabbix Server 2', url='http://zabbix2.local', token='token2')
        ZabbixServerAssignment.objects.create(zabbixserver=server2, assigned_object_type=self.device_ct, assigned_object_id=self.device1.pk)
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=device3.pk)

        job = SyncObjectsJob(job=MagicMock())
        job.run()

        # Only device1 is enqueued; the loop exits on the duplicate before reaching device3
        self.assertEqual(queue.create_job.call_count, 2)
        enqueued_instances = [call.kwargs.get('args')[0] for call in queue.create_job.call_args_list]
        self.assertIn(self.device1, enqueued_instances)
        self.assertIn(device3, enqueued_instances)

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_does_nothing_when_no_assignments_exist(self, mock_get_queue):
        job = SyncObjectsJob(job=MagicMock())
        job.run()

        mock_get_queue.assert_not_called()
