from django.test import TestCase
from django.utils.timezone import now

from nbxsync.models import ZabbixServer


class SyncInfoModelTestCase(TestCase):
    def setUp(self):
        self.zabbixserver = ZabbixServer.objects.create(name='Zabbix Test Server', description='Test server', url='http://example.com', token='dummy-token', validate_certs=True)

    def test_default_sync_fields(self):
        self.assertIsNone(self.zabbixserver.last_sync)
        self.assertFalse(self.zabbixserver.last_sync_state)
        self.assertEqual(self.zabbixserver.last_sync_message, 'Never synced')

    def test_update_sync_info_success_with_default_message(self):
        self.zabbixserver.update_sync_info(success=True)
        self.zabbixserver.refresh_from_db()

        self.assertTrue(self.zabbixserver.last_sync_state)
        self.assertEqual(self.zabbixserver.last_sync_message, 'Synchronization successful')
        self.assertIsNotNone(self.zabbixserver.last_sync)

    def test_update_sync_info_failure_with_default_message(self):
        self.zabbixserver.update_sync_info(success=False)
        self.zabbixserver.refresh_from_db()

        self.assertFalse(self.zabbixserver.last_sync_state)
        self.assertEqual(self.zabbixserver.last_sync_message, 'Synchronization failed')
        self.assertIsNotNone(self.zabbixserver.last_sync)

    def test_update_sync_info_success_with_custom_message(self):
        self.zabbixserver.update_sync_info(success=True, message='Custom success')
        self.zabbixserver.refresh_from_db()

        self.assertTrue(self.zabbixserver.last_sync_state)
        self.assertEqual(self.zabbixserver.last_sync_message, 'Custom success')

    def test_update_sync_info_failure_with_custom_message(self):
        self.zabbixserver.update_sync_info(success=False, message='Custom failure')
        self.zabbixserver.refresh_from_db()

        self.assertFalse(self.zabbixserver.last_sync_state)
        self.assertEqual(self.zabbixserver.last_sync_message, 'Custom failure')

    def test_update_sync_info_sets_last_sync(self):
        before = now()
        self.zabbixserver.update_sync_info(success=True)
        self.zabbixserver.refresh_from_db()
        after = now()

        self.assertTrue(before <= self.zabbixserver.last_sync <= after)
