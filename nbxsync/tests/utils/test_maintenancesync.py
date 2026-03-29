import datetime
from unittest.mock import MagicMock

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils.timezone import make_aware

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.choices import ZabbixMaintenanceTypeChoices, ZabbixTimePeriodTypeChoices, ZabbixTimePeriodDayofWeekChoices, ZabbixTimePeriodMonthChoices, ZabbixMaintenanceTagOperatorChoices
from nbxsync.models import ZabbixHostgroup, ZabbixMaintenance, ZabbixMaintenanceObjectAssignment, ZabbixMaintenancePeriod, ZabbixMaintenanceTagAssignment, ZabbixServer, ZabbixServerAssignment, ZabbixTag
from nbxsync.utils.sync.maintenancesync import MaintenanceSync


def make_maintenance(server, name='Test MW', maintenance_type=ZabbixMaintenanceTypeChoices.WITH_COLLECTION):
    return ZabbixMaintenance.objects.create(zabbixserver=server, name=name, active_since=make_aware(datetime.datetime(2024, 1, 1, 0, 0)), active_till=make_aware(datetime.datetime(2024, 1, 2, 0, 0)), maintenance_type=maintenance_type)


class MaintenanceSyncGetCreateParamsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix Server', url='http://zabbix.local', token='token')
        cls.mw = make_maintenance(cls.server)

    def _sync(self):
        return MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)

    def test_get_create_params_base_fields(self):
        params = self._sync().get_create_params()

        self.assertEqual(params['name'], self.mw.name)
        self.assertEqual(params['description'], self.mw.description)
        self.assertEqual(params['maintenance_type'], self.mw.maintenance_type)
        self.assertIn('active_since', params)
        self.assertIn('active_till', params)
        self.assertIsInstance(params['active_since'], int)
        self.assertIsInstance(params['active_till'], int)

    def test_get_create_params_includes_tags_for_with_collection(self):
        params = self._sync().get_create_params()

        self.assertIn('tags_evaltype', params)
        self.assertIn('tags', params)

    def test_get_create_params_excludes_tags_for_no_collection(self):
        mw = make_maintenance(self.server, name='No Collection MW', maintenance_type=ZabbixMaintenanceTypeChoices.WITHOUT_COLLECTION)
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=mw)
        params = sync.get_create_params()

        self.assertNotIn('tags_evaltype', params)
        self.assertNotIn('tags', params)

    def test_get_update_params_includes_maintenanceid(self):
        self.mw.maintenanceid = 42
        params = self._sync().get_update_params()

        self.assertEqual(params['maintenanceid'], 42)

    def test_api_object_returns_maintenance(self):
        mock_api = MagicMock()
        sync = MaintenanceSync(api=mock_api, netbox_obj=self.mw)

        self.assertEqual(sync.api_object(), mock_api.maintenance)

    def test_result_key(self):
        self.assertEqual(self._sync().result_key(), 'maintenanceids')


class MaintenanceSyncDeleteTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix Server', url='http://zabbix.local', token='token')

    def test_delete_calls_zabbix_api(self):
        mw = make_maintenance(self.server, name='Delete MW')
        mw.maintenanceid = 99
        mock_api = MagicMock()
        sync = MaintenanceSync(api=mock_api, netbox_obj=mw)

        sync.delete()

        mock_api.maintenance.delete.assert_called_once_with([99])

    def test_delete_without_maintenanceid_calls_update_sync_info(self):
        mw = make_maintenance(self.server, name='No ID MW')
        mw.maintenanceid = None
        mw.update_sync_info = MagicMock()
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=mw)

        sync.delete()

        mw.update_sync_info.assert_called_once_with(success=False, message='Maintenance already deleted or missing host ID.')

    def test_delete_raises_runtime_error_on_api_failure(self):
        mw = make_maintenance(self.server, name='Failing Delete MW')
        mw.maintenanceid = 77
        mw.update_sync_info = MagicMock()
        mock_api = MagicMock()
        mock_api.maintenance.delete.side_effect = Exception('Zabbix error')
        sync = MaintenanceSync(api=mock_api, netbox_obj=mw)

        with self.assertRaises(RuntimeError) as ctx:
            sync.delete()

        self.assertIn('77', str(ctx.exception))
        mw.update_sync_info.assert_called_once_with(success=False, message='Failed to delete maintenance: Zabbix error')


class MaintenanceSyncGetTimeperiodsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix Server', url='http://zabbix.local', token='token')
        cls.mw = make_maintenance(cls.server)

    def test_get_timeperiods_empty(self):
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        self.assertEqual(sync.get_timeperiods(), [])

    def test_get_timeperiods_one_time(self):
        ZabbixMaintenancePeriod.objects.create(zabbixmaintenance=self.mw, period=3600, timeperiod_type=ZabbixTimePeriodTypeChoices.ONE_TIME, start_date=datetime.date(2024, 3, 1), start_time=3600)
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        result = sync.get_timeperiods()

        self.assertEqual(len(result), 1)
        self.assertIn('start_date', result[0])
        self.assertIsInstance(result[0]['start_date'], int)
        self.assertNotIn('start_time', result[0])
        self.assertNotIn('every', result[0])

    def test_get_timeperiods_daily(self):
        ZabbixMaintenancePeriod.objects.create(zabbixmaintenance=self.mw, period=3600, timeperiod_type=ZabbixTimePeriodTypeChoices.DAILY, start_time=0, every=1)
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        result = sync.get_timeperiods()

        self.assertEqual(len(result), 1)
        self.assertIn('start_time', result[0])
        self.assertIn('every', result[0])
        self.assertNotIn('start_date', result[0])
        self.assertNotIn('dayofweek', result[0])

    def test_get_timeperiods_weekly_bitmask(self):
        ZabbixMaintenancePeriod.objects.create(zabbixmaintenance=self.mw, period=3600, timeperiod_type=ZabbixTimePeriodTypeChoices.WEEKLY, start_time=0, every=1, dayofweek=[ZabbixTimePeriodDayofWeekChoices.MONDAY, ZabbixTimePeriodDayofWeekChoices.WEDNESDAY])
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        result = sync.get_timeperiods()

        self.assertEqual(len(result), 1)
        # MONDAY=1, WEDNESDAY=4 → bitmask OR = 5
        self.assertEqual(result[0]['dayofweek'], 1 | 4)

    def test_get_timeperiods_monthly_by_day(self):
        ZabbixMaintenancePeriod.objects.create(zabbixmaintenance=self.mw, period=3600, timeperiod_type=ZabbixTimePeriodTypeChoices.MONTHLY, start_time=0, every=1, month=[ZabbixTimePeriodMonthChoices.JANUARY, ZabbixTimePeriodMonthChoices.MARCH], day=15)
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        result = sync.get_timeperiods()

        self.assertEqual(len(result), 1)
        # JANUARY=1, MARCH=4 -> bitmask OR = 5
        self.assertEqual(result[0]['month'], 1 | 4)
        self.assertEqual(result[0]['day'], 15)
        self.assertNotIn('dayofweek', result[0])

    def test_get_timeperiods_monthly_by_dayofweek(self):
        ZabbixMaintenancePeriod.objects.create(zabbixmaintenance=self.mw, period=3600, timeperiod_type=ZabbixTimePeriodTypeChoices.MONTHLY, start_time=0, every=1, month=[ZabbixTimePeriodMonthChoices.JANUARY], dayofweek=[ZabbixTimePeriodDayofWeekChoices.FRIDAY])
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        result = sync.get_timeperiods()

        self.assertEqual(len(result), 1)
        self.assertIn('dayofweek', result[0])
        # FRIDAY=16
        self.assertEqual(result[0]['dayofweek'], 16)
        self.assertNotIn('day', result[0])


class MaintenanceSyncGetHostsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix Server', url='http://zabbix.local', token='token')
        cls.mw = make_maintenance(cls.server)
        cls.device = create_test_device(name='Maintenance Device')
        cls.device_ct = ContentType.objects.get_for_model(Device)

    def test_get_hosts_empty(self):
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        self.assertEqual(sync.get_hosts(), [])

    def test_get_hosts_returns_hostid(self):
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.device.pk, hostid='101')
        ZabbixMaintenanceObjectAssignment.objects.create(zabbixmaintenance=self.mw, assigned_object_type=self.device_ct, assigned_object_id=self.device.pk)
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        result = sync.get_hosts()

        self.assertEqual(result, [{'hostid': 101}])

    def test_get_hosts_skips_missing_server_assignment(self):
        device2 = create_test_device(name='Unassigned Device')
        ZabbixMaintenanceObjectAssignment.objects.create(zabbixmaintenance=self.mw, assigned_object_type=self.device_ct, assigned_object_id=device2.pk)
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        result = sync.get_hosts()

        self.assertEqual(result, [])

    def test_get_hosts_skips_null_hostid(self):
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.device.pk, hostid=None)
        ZabbixMaintenanceObjectAssignment.objects.create(zabbixmaintenance=self.mw, assigned_object_type=self.device_ct, assigned_object_id=self.device.pk)
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        result = sync.get_hosts()

        self.assertEqual(result, [])


class MaintenanceSyncGetHostgroupsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix Server', url='http://zabbix.local', token='token')
        cls.mw = make_maintenance(cls.server)
        cls.hostgroup_ct = ContentType.objects.get_for_model(ZabbixHostgroup)

    def test_get_hostgroups_empty(self):
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        self.assertEqual(sync.get_hostgroups(), [])

    def test_get_hostgroups_returns_groupid(self):
        hg = ZabbixHostgroup.objects.create(name='HG1', zabbixserver=self.server, groupid=55, value='Static Group')
        ZabbixMaintenanceObjectAssignment.objects.create(zabbixmaintenance=self.mw, assigned_object_type=self.hostgroup_ct, assigned_object_id=hg.pk)
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        result = sync.get_hostgroups()

        self.assertEqual(result, [{'groupid': 55}])

    def test_get_hostgroups_skips_null_groupid(self):
        hg = ZabbixHostgroup.objects.create(name='HG No ID', zabbixserver=self.server, groupid=None, value='Static Group')
        ZabbixMaintenanceObjectAssignment.objects.create(zabbixmaintenance=self.mw, assigned_object_type=self.hostgroup_ct, assigned_object_id=hg.pk)
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        result = sync.get_hostgroups()

        self.assertEqual(result, [])


class MaintenanceSyncGetTagsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix Server', url='http://zabbix.local', token='token')
        cls.mw = make_maintenance(cls.server)

    def test_get_tags_empty(self):
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        self.assertEqual(sync.get_tags(), [])

    def test_get_tags_returns_tag_data(self):
        tag = ZabbixTag.objects.create(name='Env Tag', tag='env', value='prod')
        ZabbixMaintenanceTagAssignment.objects.create(zabbixmaintenance=self.mw, zabbixtag=tag, operator=ZabbixMaintenanceTagOperatorChoices.EQUALS, value='production')
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=self.mw)
        result = sync.get_tags()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['tag'], 'env')
        self.assertEqual(result[0]['value'], 'production')
        self.assertEqual(result[0]['operator'], ZabbixMaintenanceTagOperatorChoices.EQUALS)


class MaintenanceSyncSyncFromZabbixTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix Server', url='http://zabbix.local', token='token')

    def test_sync_from_zabbix_saves_and_updates_sync_info(self):
        mw = make_maintenance(self.server, name='Sync From Zabbix MW')
        mw.save = MagicMock()
        mw.update_sync_info = MagicMock()
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=mw)

        sync.sync_from_zabbix({})

        mw.save.assert_called_once()
        mw.update_sync_info.assert_called_once_with(success=True, message='')

    def test_sync_from_zabbix_handles_save_exception(self):
        mw = make_maintenance(self.server, name='Failing Sync MW')
        mw.save = MagicMock(side_effect=Exception('DB error'))
        mw.update_sync_info = MagicMock()
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=mw)

        sync.sync_from_zabbix({})

        mw.update_sync_info.assert_called_once_with(success=False, message='DB error')

    def test_delete_without_maintenanceid_swallows_update_sync_info_exception(self):
        mw = make_maintenance(self.server, name='Exception On Update MW')
        mw.maintenanceid = None
        mw.update_sync_info = MagicMock(side_effect=Exception('DB unavailable'))
        sync = MaintenanceSync(api=MagicMock(), netbox_obj=mw)

        # Should not raise — the except clause swallows the exception
        sync.delete()

        mw.update_sync_info.assert_called_once_with(success=False, message='Maintenance already deleted or missing host ID.')
