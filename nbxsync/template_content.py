from django.contrib.contenttypes.models import ContentType

from netbox.plugins import PluginTemplateExtension


from nbxsync.models import ZabbixHostInterface, ZabbixServerAssignment, ZabbixTemplateAssignment
from nbxsync.choices import HostInterfaceRequirementChoices
from nbxsync.utils import get_assigned_zabbixobjects, get_maintenance_can_sync


class ZabbixServerButtonsExtension(PluginTemplateExtension):
    models = ['nbxsync.zabbixserver']

    def buttons(self):
        return self.render('nbxsync/buttons/synctemplate.html')


class ZabbixProxyButtonsExtension(PluginTemplateExtension):
    models = ['nbxsync.zabbixproxy']

    def buttons(self):
        return self.render('nbxsync/buttons/syncproxy.html')


class ZabbixProxyGroupButtonsExtension(PluginTemplateExtension):
    models = ['nbxsync.zabbixproxygroup']

    def buttons(self):
        return self.render('nbxsync/buttons/syncproxygroup.html')


class ZabbixMaintenanceButtonsExtension(PluginTemplateExtension):
    models = ['nbxsync.zabbixmaintenance']

    def buttons(self):
        obj = self.context.get('object')
        if not obj:
            return ''

        return self.render(
            'nbxsync/buttons/syncmaintenance.html',
            extra_context={
                'can_sync': get_maintenance_can_sync(obj),
            },
        )


class ZabbixDeviceButtonsExtension(PluginTemplateExtension):
    models = ['dcim.device', 'dcim.virtualdevicecontext', 'virtualization.virtualmachine']

    def buttons(self):
        obj = self.context.get('object')
        if not obj:
            return ''

        ct = ContentType.objects.get_for_model(obj)
        has_server_assignment = ZabbixServerAssignment.objects.filter(assigned_object_type=ct, assigned_object_id=obj.pk).exists()

        hostgroups = get_assigned_zabbixobjects(obj).get('hostgroups') or []
        has_hostgroup_assignment = bool(hostgroups)

        assigned_hostinterface_types = set(ZabbixHostInterface.objects.filter(assigned_object_type=ct, assigned_object_id=obj.pk).values_list('type', flat=True).distinct())
        assigned_zabbixtemplates = list(ZabbixTemplateAssignment.objects.filter(assigned_object_type=ct, assigned_object_id=obj.pk))

        has_hostinterface_assignment = True

        for assigned_template in assigned_zabbixtemplates:
            required = set(assigned_template.zabbixtemplate.interface_requirements or [])
            has_none = HostInterfaceRequirementChoices.NONE in required
            has_any = HostInterfaceRequirementChoices.ANY in required
            actual_required = required - {HostInterfaceRequirementChoices.NONE, HostInterfaceRequirementChoices.ANY}

            if has_none and not has_any and not actual_required:
                template_ok = True
            else:
                any_ok = bool(assigned_hostinterface_types) if has_any else True
                specific_ok = actual_required.issubset(assigned_hostinterface_types) if actual_required else True
                template_ok = any_ok and specific_ok

            # Break out of the loop / checks if it has failed once, no need to further evaluate other options
            if not template_ok:
                has_hostinterface_assignment = False
                break

            has_hostinterface_assignment = has_hostinterface_assignment and template_ok

        return self.render(
            'nbxsync/buttons/synchost.html',
            extra_context={
                'can_sync': has_server_assignment and has_hostinterface_assignment and has_hostgroup_assignment,
                'object': obj,
            },
        )


class ZabbixConfigurationGroupButtonsExtension(PluginTemplateExtension):
    models = ['nbxsync.zabbixconfigurationgroup']

    def buttons(self):
        obj = self.context.get('object')
        if not obj:
            return ''

        return self.render(
            'nbxsync/buttons/syncconfigurationgroup.html',
            extra_context={
                'object': obj,
            },
        )


template_extensions = [
    ZabbixServerButtonsExtension,
    ZabbixProxyButtonsExtension,
    ZabbixProxyGroupButtonsExtension,
    ZabbixDeviceButtonsExtension,
    ZabbixMaintenanceButtonsExtension,
    ZabbixConfigurationGroupButtonsExtension,
]
