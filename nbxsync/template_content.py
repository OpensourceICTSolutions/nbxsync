from django.contrib.contenttypes.models import ContentType

from netbox.plugins import PluginTemplateExtension

from nbxsync.models import ZabbixHostInterface, ZabbixServerAssignment, ZabbixTemplateAssignment
from nbxsync.choices import HostInterfaceRequirementChoices
from nbxsync.utils import get_assigned_zabbixobjects


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
        return self.render('nbxsync/buttons/syncmaintenance.html')


class ZabbixDeviceButtonsExtension(PluginTemplateExtension):
    models = ['dcim.device', 'dcim.virtualdevicecontext', 'virtualization.virtualmachine']

    def buttons(self):
        object = self.context.get('object')
        if not object:
            return ''

        ct = ContentType.objects.get_for_model(object)
        has_server_assignment = ZabbixServerAssignment.objects.filter(assigned_object_type=ct, assigned_object_id=object.pk).exists()
        has_hostinterface_assignment = False
        has_hostgroup_assignment = False

        all_objects = get_assigned_zabbixobjects(object)
        if len(all_objects['hostgroups']) > 0:
            has_hostgroup_assignment = True

        assigned_hostinterface_types = set(ZabbixHostInterface.objects.filter(assigned_object_type=ct, assigned_object_id=object.pk).values_list('type', flat=True).distinct())
        assigned_zabbixtemplates = ZabbixTemplateAssignment.objects.filter(assigned_object_type=ct, assigned_object_id=object.pk)

        # If there are no templates, there is no requirement for any interface
        # So, set it to true
        if len(assigned_zabbixtemplates) == 0:
            has_hostinterface_assignment = True

        # Next step:
        # Loop through all Templates and gather all required interfaces
        for assigned_template in assigned_zabbixtemplates:
            # Extract requirement flags/sets
            required = set(assigned_template.zabbixtemplate.interface_requirements or [])
            has_none = HostInterfaceRequirementChoices.NONE in required
            has_any = HostInterfaceRequirementChoices.ANY in required
            actual_required = required - {HostInterfaceRequirementChoices.NONE, HostInterfaceRequirementChoices.ANY}

            # Evaluate
            if has_none and not has_any and not actual_required:
                # "NONE" only → no interfaces required
                has_hostinterface_assignment = True
            else:
                # If "ANY" is present, require at least one assigned interface
                any_ok = (len(assigned_hostinterface_types) > 0) if has_any else True

                # If specific types are present, require all of them
                specific_ok = actual_required.issubset(assigned_hostinterface_types) if actual_required else True

                has_hostinterface_assignment = any_ok and specific_ok

        return self.render(
            'nbxsync/buttons/synchost.html',
            extra_context={
                'can_sync': has_server_assignment and has_hostinterface_assignment and has_hostgroup_assignment,
                'object': object,
            },
        )


template_extensions = [
    ZabbixServerButtonsExtension,
    ZabbixProxyButtonsExtension,
    ZabbixProxyGroupButtonsExtension,
    ZabbixDeviceButtonsExtension,
    ZabbixMaintenanceButtonsExtension,
]
