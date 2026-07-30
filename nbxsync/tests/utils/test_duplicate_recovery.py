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
