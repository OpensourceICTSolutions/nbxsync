from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.models import ZabbixHostBinding, ZabbixServer, ZabbixServerAssignment
from nbxsync.signals.nbobjects import handle_deleted_object


class NetBoxObjectDeleteSignalTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix', url='http://zabbix.local', token='token')
        cls.device = create_test_device(name='delete-signal-device')
        cls.device_ct = ContentType.objects.get_for_model(Device)

    @patch('nbxsync.signals.nbobjects.get_queue')
    def test_delete_is_enqueued_after_commit_with_binding_ids(self, mock_get_queue):
        binding = ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=4_000_000_001,
            hostname=self.device.name,
        )
        queue = MagicMock()
        mock_get_queue.return_value = queue

        with self.captureOnCommitCallbacks(execute=True):
            handle_deleted_object(Device, self.device)
            mock_get_queue.assert_not_called()

        mock_get_queue.assert_called_once_with('low')
        _, kwargs = queue.create_job.call_args
        self.assertEqual(kwargs['func'], 'nbxsync.worker.deletehost')
        self.assertEqual(kwargs['args'], [(binding.pk,)])
        self.assertEqual(kwargs['retry'].max, 5)
        self.assertTrue(ZabbixHostBinding.objects.filter(pk=binding.pk).exists())

    @patch('nbxsync.signals.nbobjects.get_queue')
    def test_delete_migrates_legacy_direct_hostid_before_commit(self, mock_get_queue):
        assignment = ZabbixServerAssignment.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=4_000_000_004,
        )
        queue = MagicMock()
        mock_get_queue.return_value = queue

        with self.captureOnCommitCallbacks(execute=True):
            handle_deleted_object(Device, self.device)

        binding = ZabbixHostBinding.objects.get(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
        )
        self.assertEqual(binding.hostid, assignment.hostid)
        _, kwargs = queue.create_job.call_args
        self.assertEqual(kwargs['args'], [(binding.pk,)])

    @patch('nbxsync.signals.nbobjects.get_queue')
    def test_delete_without_binding_does_not_enqueue_unsafe_name_lookup(self, mock_get_queue):
        with self.captureOnCommitCallbacks(execute=True):
            handle_deleted_object(Device, self.device)

        mock_get_queue.assert_not_called()
