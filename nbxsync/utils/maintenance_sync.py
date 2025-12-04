from django.contrib.contenttypes.models import ContentType

from dcim.models import Device, VirtualDeviceContext
from virtualization.models import VirtualMachine

from nbxsync.models import ZabbixMaintenanceObjectAssignment, ZabbixMaintenancePeriod, ZabbixHostgroup


def get_maintenance_can_sync(obj):
    ct_map = ContentType.objects.get_for_models(ZabbixHostgroup, Device, VirtualMachine, VirtualDeviceContext)
    zabbixhostgroup_ct = ct_map[ZabbixHostgroup]
    device_ct = ct_map[Device]
    virtualmachine_ct = ct_map[VirtualMachine]
    vdc_ct = ct_map[VirtualDeviceContext]

    assignments = ZabbixMaintenanceObjectAssignment.objects.filter(zabbixmaintenance=obj.pk)
    has_hostgroup = assignments.filter(assigned_object_type=zabbixhostgroup_ct).exists()
    has_host = assignments.filter(assigned_object_type__in=[device_ct, virtualmachine_ct, vdc_ct]).exists()

    has_timeperiod = ZabbixMaintenancePeriod.objects.filter(zabbixmaintenance=obj.pk).exists()

    return has_timeperiod and (has_hostgroup or has_host)
