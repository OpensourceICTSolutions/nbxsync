from django.db.models import Q

ASSIGNMENT_MODELS = Q(
    Q(app_label='dcim', model='device')
    | Q(app_label='dcim', model='virtualdevicecontext')
    | Q(app_label='dcim', model='manufacturer')
    | Q(app_label='dcim', model='devicerole')
    | Q(app_label='dcim', model='devicetype')
    | Q(app_label='dcim', model='platform')
    | Q(app_label='virtualization', model='virtualmachine')
    | Q(app_label='virtualization', model='cluster')
    | Q(app_label='virtualization', model='clustertype')
)
DEVICE_OR_VM_ASSIGNMENT_MODELS = Q(Q(app_label='dcim', model='device') | Q(app_label='dcim', model='virtualdevicecontext') | Q(app_label='virtualization', model='virtualmachine'))
MACRO_ASSIGNMENT_MODELS = Q(Q(app_label='nbxsync', model='zabbixserver') | Q(app_label='nbxsync', model='zabbixtemplate'))
MAINTENANCE_ASSIGNMENT_OBJECTS = Q(Q(Q(app_label='nbxsync', model='zabbixhostgroup')) | DEVICE_OR_VM_ASSIGNMENT_MODELS)
MAINTENANCE_ASSIGNMENT_TAGS = Q(app_label='nbxsync', model='zabbixtag')

CONFIGGROUP_OBJECTS = Q(app_label='nbxsync', model='zabbixconfigurationgroup')
