"""Tests for recovering from a concurrent create in Zabbix.

Two workers can create the same hostgroup/proxy/template between the lookup and
the create call. Recovering from that race must not swallow genuine validation
errors, so only Zabbix's -32602 'already exists' response is treated as a race.
"""

from django.test import TestCase

from nbxsync.utils.sync.syncbase import ZabbixSyncBase


class _ApiError(Exception):
    def __init__(self, message, code=None, data=''):
        super().__init__(f'{message} {data}'.strip())
        if code is not None:
            self.code = code
        self.data = data
        self.message = message


class DuplicateErrorDetectionTestCase(TestCase):
    def test_duplicate_params_error_is_recognised(self):
        err = _ApiError('Invalid params.', code=-32602, data='Host group "Linux servers" already exists.')

        self.assertTrue(ZabbixSyncBase._is_duplicate_error(err))

    def test_other_invalid_params_error_is_not_a_duplicate(self):
        err = _ApiError('Invalid params.', code=-32602, data='Incorrect value for field "name": cannot be empty.')

        self.assertFalse(ZabbixSyncBase._is_duplicate_error(err))

    def test_internal_error_is_not_a_duplicate(self):
        err = _ApiError('Internal error.', code=-32500, data='already exists somewhere')

        self.assertFalse(ZabbixSyncBase._is_duplicate_error(err))

    def test_plain_exception_falls_back_to_the_message(self):
        self.assertTrue(ZabbixSyncBase._is_duplicate_error(Exception('Host group already exists')))
        self.assertFalse(ZabbixSyncBase._is_duplicate_error(Exception('Connection refused')))


class _FakeApiObject:
    def __init__(self, update_side_effect=None):
        self.update_side_effect = update_side_effect
        self.update_calls = 0

    def update(self, **params):
        self.update_calls += 1
        if self.update_side_effect is not None:
            raise self.update_side_effect


class _UpdateSync(ZabbixSyncBase):
    id_field = 'groupid'
    name_field = 'name'

    def __init__(self, api_object):
        self._api = api_object
        self.obj = type('Obj', (), {'groupid': '23', 'name': 'Priority/Critical'})()

    def api_object(self):
        return self._api

    def get_update_params(self, object_id=None):
        return {'groupid': object_id or self.get_id(), 'name': self.obj.name}


class UpdateDuplicateRecoveryTestCase(TestCase):
    def test_update_already_exists_is_treated_as_noop(self):
        err = _ApiError('Invalid params.', code=-32602, data='Host group "Priority/Critical" already exists.')
        api = _FakeApiObject(update_side_effect=err)
        sync = _UpdateSync(api)

        sync.update_in_zabbix(object_id='23')

        self.assertEqual(api.update_calls, 1)

    def test_update_other_errors_still_raise(self):
        err = _ApiError('Invalid params.', code=-32602, data='Incorrect value for field "name": cannot be empty.')
        api = _FakeApiObject(update_side_effect=err)
        sync = _UpdateSync(api)

        with self.assertRaises(_ApiError):
            sync.update_in_zabbix(object_id='23')
