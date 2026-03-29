import datetime

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils.timezone import make_aware

from dcim.models import Device, VirtualDeviceContext
from utilities.testing import create_test_device, create_test_virtualmachine
from virtualization.models import VirtualMachine

from nbxsync.models import (
    ZabbixHostgroup,
    ZabbixMaintenance,
    ZabbixMaintenanceObjectAssignment,
    ZabbixMaintenancePeriod,
    ZabbixServer,
)
from nbxsync.utils.maintenance_sync import get_maintenance_can_sync


def make_maintenance(server, name='Test MW'):
    return ZabbixMaintenance.objects.create(zabbixserver=server, name=name, active_since=make_aware(datetime.datetime(2024, 1, 1, 0, 0)), active_till=make_aware(datetime.datetime(2024, 1, 2, 0, 0)))


def make_timeperiod(mw):
    return ZabbixMaintenancePeriod.objects.create(
        zabbixmaintenance=mw,
        period=3600,
        timeperiod_type=0,  # ONE_TIME
        start_date=datetime.date(2024, 3, 1),
        start_time=0,
    )


class GetMaintenanceCanSyncTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix Server', url='http://zabbix.local', token='token')
        cls.device = create_test_device(name='Maintenance Device')
        cls.vm = create_test_virtualmachine(name='Maintenance VM')
        cls.vdc = VirtualDeviceContext.objects.create(device=cls.device, name='Test VDC', status='active')
        cls.hostgroup = ZabbixHostgroup.objects.create(name='HG1', zabbixserver=cls.server, groupid=1, value='Static Group')

        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.vm_ct = ContentType.objects.get_for_model(VirtualMachine)
        cls.vdc_ct = ContentType.objects.get_for_model(VirtualDeviceContext)
        cls.hostgroup_ct = ContentType.objects.get_for_model(ZabbixHostgroup)

    def test_returns_false_when_no_timeperiod_and_no_assignment(self):
        mw = make_maintenance(self.server, name='Empty MW')
        self.assertFalse(get_maintenance_can_sync(mw))

    def test_returns_false_when_timeperiod_missing_but_host_assigned(self):
        mw = make_maintenance(self.server, name='No Period MW')
        ZabbixMaintenanceObjectAssignment.objects.create(zabbixmaintenance=mw, assigned_object_type=self.device_ct, assigned_object_id=self.device.pk)

        self.assertFalse(get_maintenance_can_sync(mw))

    def test_returns_false_when_timeperiod_present_but_no_assignment(self):
        mw = make_maintenance(self.server, name='No Assignment MW')
        make_timeperiod(mw)

        self.assertFalse(get_maintenance_can_sync(mw))

    def test_returns_true_with_timeperiod_and_device(self):
        mw = make_maintenance(self.server, name='Device MW')
        make_timeperiod(mw)
        ZabbixMaintenanceObjectAssignment.objects.create(zabbixmaintenance=mw, assigned_object_type=self.device_ct, assigned_object_id=self.device.pk)

        self.assertTrue(get_maintenance_can_sync(mw))

    def test_returns_true_with_timeperiod_and_virtualmachine(self):
        mw = make_maintenance(self.server, name='VM MW')
        make_timeperiod(mw)
        ZabbixMaintenanceObjectAssignment.objects.create(zabbixmaintenance=mw, assigned_object_type=self.vm_ct, assigned_object_id=self.vm.pk)

        self.assertTrue(get_maintenance_can_sync(mw))

    def test_returns_true_with_timeperiod_and_vdc(self):
        mw = make_maintenance(self.server, name='VDC MW')
        make_timeperiod(mw)
        ZabbixMaintenanceObjectAssignment.objects.create(zabbixmaintenance=mw, assigned_object_type=self.vdc_ct, assigned_object_id=self.vdc.pk)

        self.assertTrue(get_maintenance_can_sync(mw))

    def test_returns_true_with_timeperiod_and_hostgroup(self):
        mw = make_maintenance(self.server, name='Hostgroup MW')
        make_timeperiod(mw)
        ZabbixMaintenanceObjectAssignment.objects.create(zabbixmaintenance=mw, assigned_object_type=self.hostgroup_ct, assigned_object_id=self.hostgroup.pk)

        self.assertTrue(get_maintenance_can_sync(mw))
