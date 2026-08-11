from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from dcim.models import Device
from utilities.testing import create_test_device
from nbxsync.models import ZabbixServer, ZabbixServerAssignment


def _make_event(eventid, clock, r_eventid='0', **extra):
    base = {
        'eventid': eventid,
        'clock': clock,
        'r_eventid': r_eventid,
        'name': f'Event {eventid}',
        'severity': '4',
        'objectid': '9999',
        'acknowledged': '0',
        'opdata': '',
    }
    base.update(extra)
    return base


class HostEventsViewOpenEventTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.device = create_test_device(name='dev1')
        cls.server = ZabbixServer.objects.create(name='ZBX', url='http://example.com', token='test')
        cls.assignment = ZabbixServerAssignment.objects.create(zabbixserver=cls.server, hostid=101, assigned_object_type=ContentType.objects.get_for_model(Device), assigned_object_id=cls.device.pk)

    @patch('nbxsync.views.hostinfo.ZabbixConnection')
    def test_first_event_is_still_open_does_not_raise(self, mock_conn):
        api = MagicMock()
        api.event.get.return_value = [_make_event('1', '1000')]
        mock_conn.return_value.__enter__.return_value = api

        response = self.client.get(reverse('plugins:nbxsync:zabbixhost_events', kwargs={'objtype': 'device', 'pk': self.device.pk}))
        self.assertEqual(response.status_code, 200)

        rows = list(response.context['table'].rows)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0].record['end_time'])
        self.assertIsNone(rows[0].record['duration'])

    @patch('nbxsync.views.hostinfo.ZabbixConnection')
    def test_open_event_after_recovered_event_uses_own_state(self, mock_conn):
        api = MagicMock()
        api.event.get.return_value = [
            _make_event('1', '1000', r_eventid='2'),  # recovered
            _make_event('2', '1500'),  # its recovery
            _make_event('3', '2000'),  # open — must not inherit '1500'
        ]
        mock_conn.return_value.__enter__.return_value = api

        response = self.client.get(reverse('plugins:nbxsync:zabbixhost_events', kwargs={'objtype': 'device', 'pk': self.device.pk}))
        rows = [r.record for r in response.context['table'].rows]
        open_row = next(r for r in rows if r['eventid'] == '3')
        self.assertIsNone(open_row['end_time'])
        self.assertIsNone(open_row['duration'])
