from dcim.models import Device, VirtualDeviceContext, DeviceRole, DeviceType, Manufacturer, Platform
from virtualization.models import Cluster, ClusterType, VirtualMachine

from nbxsync.models import ZabbixHostgroup, ZabbixServer, ZabbixTag, ZabbixTemplate, ZabbixConfigurationGroup


ASSIGNMENT_TYPE_TO_FIELD_NBOBJS = {
    Device: 'device',
    DeviceType: 'devicetype',
    DeviceRole: 'role',
    Manufacturer: 'manufacturer',
    Platform: 'platform',
    VirtualMachine: 'virtualmachine',
    Cluster: 'cluster',
    ClusterType: 'clustertype',
    VirtualDeviceContext: 'virtualdevicecontext',
    ZabbixConfigurationGroup: 'zabbixconfigurationgroup',
}

ASSIGNMENT_TYPE_TO_FIELD = {
    **ASSIGNMENT_TYPE_TO_FIELD_NBOBJS.copy(),
    ZabbixServer: 'zabbixserver',
    ZabbixTemplate: 'zabbixtemplate',
    ZabbixConfigurationGroup: 'zabbixconfigurationgroup',
}

ASSIGNMENT_TYPE_TO_FIELD_MAINTENANCE = {
    Device: 'device',
    VirtualMachine: 'virtualmachine',
    VirtualDeviceContext: 'virtualdevicecontext',
    ZabbixHostgroup: 'zabbixhostgroup',
}

OBJECT_TYPE_MODEL_MAP = {
    'device': Device,
    'virtualmachine': VirtualMachine,
    'virtualdevicecontext': VirtualDeviceContext,
    'zabbixconfigurationgroup': ZabbixConfigurationGroup,
}


ASSIGNMENT_TAGTYPE_TO_FIELD_MAINTENANCE = {ZabbixTag: 'zabbixtag'}
