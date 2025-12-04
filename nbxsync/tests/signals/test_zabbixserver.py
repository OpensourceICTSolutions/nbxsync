from unittest.mock import MagicMock, patch

from django.test import TestCase

from nbxsync.models import ZabbixServer

import nbxsync.signals.zabbixserver  # noqa: F401


class ZabbixServerSignalsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix Server 1', description='Primary test server', url='http://example.com', token='test-token', validate_certs=True)

    def test_track_changes_on_create_sets_empty_changed_fields(self):
        server = ZabbixServer.objects.create(name='New Zabbix Server', description='New server description', url='http://new.example.com', token='new-token', validate_certs=False)

        self.assertTrue(hasattr(server, '_changed_fields'))
        self.assertEqual(server._changed_fields, [])

    def test_track_changes_on_update_detects_changed_fields(self):
        server = ZabbixServer.objects.get(pk=self.server.pk)

        server.name = 'Renamed Server'
        server.description = 'Updated description'
        server.save()

        self.assertTrue(hasattr(server, '_changed_fields'))

        self.assertIn('name', server._changed_fields)
        self.assertIn('description', server._changed_fields)

    @patch('nbxsync.signals.zabbixserver.get_queue')
    def test_postsave_created_enqueues_job(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        server = ZabbixServer.objects.create(name='Created Server', description='Server created in test', url='http://created.example.com', token='created-token', validate_certs=True)

        mock_get_queue.assert_called_once_with('low')
        queue.create_job.assert_called_once()

        args, kwargs = queue.create_job.call_args

        func = kwargs.get('func', args[0] if args else None)
        job_args = kwargs.get('args', args[1] if len(args) > 1 else None)
        timeout = kwargs.get('timeout', args[2] if len(args) > 2 else None)

        self.assertEqual(func, 'nbxsync.worker.synctemplates')
        self.assertEqual(job_args, [server])
        self.assertEqual(timeout, 9000)

        queue.enqueue_job.assert_called_once_with(queue.create_job.return_value)

    @patch('nbxsync.signals.zabbixserver.get_queue')
    def test_postsave_update_non_sync_fields_enqueues_job(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        server = ZabbixServer.objects.get(pk=self.server.pk)
        server.name = 'Updated Name'
        server.description = 'Changed description'
        server.save()

        mock_get_queue.assert_called_once_with('low')
        queue.create_job.assert_called_once()
        queue.enqueue_job.assert_called_once_with(queue.create_job.return_value)

    @patch('nbxsync.signals.zabbixserver.get_queue')
    def test_postsave_update_sync_field_does_not_enqueue_job(self, mock_get_queue):
        server = ZabbixServer.objects.get(pk=self.server.pk)

        server.last_sync_message = 'Sync changed in test'
        server.save()

        mock_get_queue.assert_not_called()
