from unittest.mock import MagicMock, patch

from django.test import TestCase

from nbxsync.choices.syncsot import SyncSOT
from nbxsync.utils.resolve_zabbixserver import resolve_zabbixserver
from nbxsync.utils.sync.syncbase import ZabbixSyncBase


class DummyObject:
    def __init__(self, name='TestObj', id=123):
        self.name = name
        self.id = id
        self.from_zabbix = False
        self._updated = {}
        self._saved = False

    def save(self):
        self._saved = True

    def update_sync_info(self, **kwargs):
        self._updated = kwargs


class DummySync(ZabbixSyncBase):
    id_field = 'id'
    sot_key = 'dummy'

    def api_object(self):
        return self.api.dummy

    def get_create_params(self, **kwargs):
        return {'name': 'test'}

    def get_update_params(self, **kwargs):
        return {'id': self.obj.id, 'name': 'updated'}

    def result_key(self):
        return 'dummyids'

    def sync_from_zabbix(self, data):
        self.obj.from_zabbix = True


class IncompleteSync(ZabbixSyncBase):
    id_field = 'id'
    sot_key = 'dummy'


class ZabbixSyncBaseTests(TestCase):
    def setUp(self):
        self.obj = DummyObject()
        self.api = MagicMock()
        self.api.dummy.get.return_value = [{'id': 123}]
        self.api.dummy.create.return_value = {'dummyids': ['123']}
        self.api.dummy.update.return_value = {'dummyids': ['123']}

        patcher = patch('nbxsync.utils.sync.syncbase.get_plugin_settings')
        self.addCleanup(patcher.stop)
        mock_settings = patcher.start()
        mock_settings.return_value.sot.dummy = SyncSOT.ZABBIX

        self.sync = DummySync(api=self.api, netbox_obj=self.obj)

    def test_get_id_key(self):
        self.assertEqual(self.sync.get_id_key(), 'id')

    def test_get_id(self):
        self.assertEqual(self.sync.get_id(), 123)

    def test_get_id_handles_missing_attr(self):
        broken_sync = DummySync(api=self.api, netbox_obj=object())
        self.assertIsNone(broken_sync.get_id())

    def test_set_id_sets_and_saves(self):
        class Parent:
            def __init__(self):
                self.child = DummyObject()

        parent = Parent()
        self.sync.obj = parent
        self.sync.id_field = 'child.id'
        self.sync.set_id(999)
        self.assertEqual(parent.child.id, 999)
        self.assertTrue(parent.child._saved)

    def test_find_by_name(self):
        result = self.sync.find_by_name()
        self.assertEqual(result, [{'id': 123}])

    def test_find_by_id(self):
        result = self.sync.find_by_id()
        self.assertEqual(result, [{'id': 123}])

    def test_try_create_success(self):
        result = self.sync.try_create()
        self.assertEqual(result, '123')

    def test_try_create_failure(self):
        self.api.dummy.create.side_effect = Exception('fail')
        with self.assertRaises(RuntimeError):
            self.sync.try_create()

    def test_sync_to_zabbix(self):
        self.sync.sync_to_zabbix('200')
        self.assertEqual(self.obj.id, '200')
        self.assertTrue(self.obj._updated['success'])

    def test_update_in_zabbix(self):
        self.sync.update_in_zabbix()
        self.api.dummy.update.assert_called_once()

    def test_handle_found_zabbix(self):
        self.sync.sot = SyncSOT.ZABBIX
        result = self.sync.handle_found({'id': 111})
        self.assertEqual(result, 111)
        self.assertTrue(self.obj.from_zabbix)

    def test_handle_found_netbox(self):
        self.sync.sot = SyncSOT.NETBOX
        result = self.sync.handle_found({'id': 222})
        self.assertEqual(result, 222)
        self.assertTrue(self.obj._updated['success'])

    def test_sync_found_by_id(self):
        self.sync.get_id = MagicMock(return_value=123)
        self.sync.find_by_id = MagicMock(return_value=[{'id': 123}])
        self.sync.find_by_name = MagicMock(return_value=[])
        self.sync.sync()

    def test_sync_found_by_name(self):
        self.sync.get_id = MagicMock(return_value=None)
        self.sync.find_by_name = MagicMock(return_value=[{'id': 123}])
        self.sync.sync()

    def test_sync_creates_if_not_found(self):
        self.sync.get_id = MagicMock(return_value=None)
        self.sync.find_by_name = MagicMock(return_value=[])
        self.sync.sync()
        self.assertEqual(self.obj.id, '123')
        self.assertTrue(self.obj._updated['success'])

    def test_sync_create_fails_runtime(self):
        self.sync.get_id = MagicMock(return_value=None)
        self.sync.find_by_name = MagicMock(return_value=[])
        self.api.dummy.create.side_effect = Exception('fail')

        with self.assertRaises(RuntimeError):
            self.sync.sync()

    def test_get_name_value_with_name_field(self):
        self.sync.name_field = 'name'
        result = self.sync.get_name_value()
        self.assertEqual(result, 'TestObj')

    def test_get_name_value_fallback_to_obj_name(self):
        self.sync.name_field = None
        result = self.sync.get_name_value()
        self.assertEqual(result, 'TestObj')

    def test_sync_from_zabbix_not_implemented(self):
        incomplete = IncompleteSync(api=self.api, netbox_obj=self.obj)
        with self.assertRaises(NotImplementedError):
            incomplete.sync_from_zabbix({})

    def test_delete_raises_not_implemented(self):
        incomplete = IncompleteSync(api=self.api, netbox_obj=self.obj)
        with self.assertRaises(NotImplementedError):
            incomplete.delete()

    def test_api_object_raises_not_implemented(self):
        incomplete = IncompleteSync(api=self.api, netbox_obj=self.obj)
        with self.assertRaises(NotImplementedError):
            incomplete.api_object()

    def test_get_create_params_raises_not_implemented(self):
        incomplete = IncompleteSync(api=self.api, netbox_obj=self.obj)
        with self.assertRaises(NotImplementedError):
            incomplete.get_create_params()

    def test_get_update_params_raises_not_implemented(self):
        incomplete = IncompleteSync(api=self.api, netbox_obj=self.obj)
        with self.assertRaises(NotImplementedError):
            incomplete.get_update_params()

    def test_result_key_raises_not_implemented(self):
        incomplete = IncompleteSync(api=self.api, netbox_obj=self.obj)
        with self.assertRaises(NotImplementedError):
            incomplete.result_key()

    def test_missing_sot_key_raises_value_error(self):
        class NoSOTKey(ZabbixSyncBase):
            id_field = 'id'
            # Missing sot_key

        with self.assertRaises(ValueError) as ctx:
            NoSOTKey(api=self.api, netbox_obj=self.obj)
        self.assertIn('must define `sot_key`', str(ctx.exception))

    def test_missing_sot_setting_raises_value_error(self):
        class InvalidSOTKey(ZabbixSyncBase):
            id_field = 'id'
            sot_key = 'invalid_key'

        with patch('nbxsync.utils.sync.syncbase.get_plugin_settings') as mock_settings:
            mock_settings.return_value.sot.invalid_key = None
            with self.assertRaises(ValueError) as ctx:
                InvalidSOTKey(api=self.api, netbox_obj=self.obj)
            self.assertIn("No source-of-truth setting found for key 'invalid_key'", str(ctx.exception))

    def test_resolve_zabbixserver_callable(self):
        class Custom(ZabbixSyncBase):
            id_field = 'id'
            sot_key = 'dummy'
            zabbixserver_path = staticmethod(lambda obj: 'called')

        with patch('nbxsync.utils.sync.syncbase.get_plugin_settings') as mock_settings:
            mock_settings.return_value.sot.dummy = SyncSOT.ZABBIX
            self.assertEqual(Custom.resolve_zabbixserver(object()), 'called')

    def test_resolve_zabbixserver_fallback(self):
        class Custom(ZabbixSyncBase):
            id_field = 'id'
            sot_key = 'dummy'
            zabbixserver_path = 'nested.attr'

        with (
            patch('nbxsync.utils.sync.syncbase.get_plugin_settings') as mock_settings,
            patch('nbxsync.utils.sync.syncbase.resolve_zabbixserver') as mock_resolve,
        ):
            mock_settings.return_value.sot.dummy = SyncSOT.ZABBIX
            mock_resolve.return_value = 'fallback-value'
            self.assertEqual(Custom.resolve_zabbixserver(object()), 'fallback-value')
            mock_resolve.assert_called_once()

    def test_sync_falls_back_to_name_if_id_not_found(self):
        self.sync.get_id = MagicMock(return_value=123)
        self.sync.find_by_id = MagicMock(return_value=[])
        self.sync.find_by_name = MagicMock(return_value=[{'id': 123}])
        self.sync.sync_from_zabbix = MagicMock()
        self.sync.sync()
        self.sync.sync_from_zabbix.assert_called_once()

    def test_sync_to_zabbix_called_when_sot_netbox(self):
        with patch('nbxsync.utils.sync.syncbase.get_plugin_settings') as mock_settings:
            mock_settings.return_value.sot.dummy = SyncSOT.NETBOX
            sync = DummySync(api=self.api, netbox_obj=self.obj)
            sync.sync_to_zabbix = MagicMock()
            sync.get_id = MagicMock(return_value=123)
            sync.find_by_id = MagicMock(return_value=[{'id': 123}])
            sync.sync()
            sync.sync_to_zabbix.assert_called_once_with(123)

    def test_sync_raises_runtime_if_creation_returns_no_id(self):
        self.sync.get_id = MagicMock(return_value=None)
        self.sync.find_by_name = MagicMock(return_value=[])
        self.sync.api_object().create.return_value = {'dummyids': [None]}

        with self.assertRaises(RuntimeError) as ctx:
            self.sync.sync()
        self.assertIn('DummySync creation returned no ID', str(ctx.exception))

    class NoZabbixAttrs:
        pass

    def test_resolve_zabbixserver_fallback_path_invalid(self):
        obj = self.NoZabbixAttrs()
        result = resolve_zabbixserver(obj, fallback_path='nonexistent.path')
        self.assertIsNone(result)

    def test_resolve_zabbixserver_with_no_fallback_path(self):
        obj = self.NoZabbixAttrs()
        result = resolve_zabbixserver(obj, fallback_path=None)
        self.assertIsNone(result)
