from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet, TabbedGroups
from dcim.models import Device, VirtualDeviceContext
from virtualization.models import VirtualMachine

from nbxsync.constants import ASSIGNMENT_TYPE_TO_FIELD_MAINTENANCE
from nbxsync.models import ZabbixHostgroup, ZabbixMaintenance, ZabbixMaintenanceObjectAssignment

__all__ = ('ZabbixMaintenanceObjectAssignmentForm', 'ZabbixMaintenanceObjectAssignmentFilterForm', 'ZabbixMaintenanceObjectAssignmentBulkEditForm')


class ZabbixMaintenanceObjectAssignmentForm(NetBoxModelForm):
    zabbixmaintenance = DynamicModelChoiceField(queryset=ZabbixMaintenance.objects.all(), required=True, selector=True, label=_('Zabbix Maintenance'))
    zabbixhostgroup = DynamicModelChoiceField(queryset=ZabbixHostgroup.objects.all(), required=False, selector=True, query_params={'is_template': False}, label=_('Zabbix Hostgroup'), help_text=_('Static only, no templated hostgroups'))
    device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False, selector=True, label=_('Device'))
    virtualdevicecontext = DynamicModelChoiceField(queryset=VirtualDeviceContext.objects.all(), required=False, selector=True, label=_('Virtual Device Context'))
    virtualmachine = DynamicModelChoiceField(queryset=VirtualMachine.objects.all(), required=False, selector=True, label=_('Virtual Machine'))

    fieldsets = (
        FieldSet('zabbixmaintenance', name=_('Generic')),
        FieldSet(
            TabbedGroups(
                FieldSet('device', name=_('Device')),
                FieldSet('virtualdevicecontext', name=_('Virtual Device Context')),
                FieldSet('virtualmachine', name=_('Virtual Machine')),
                FieldSet('zabbixhostgroup', name=_('Hostgroup')),
            ),
            name=_('Assignment'),
        ),
    )

    class Meta:
        model = ZabbixMaintenanceObjectAssignment
        fields = (
            'zabbixmaintenance',
            'zabbixhostgroup',
            'device',
            'virtualdevicecontext',
            'virtualmachine',
        )

    @property
    def assignable_fields(self):
        return list(ASSIGNMENT_TYPE_TO_FIELD_MAINTENANCE.values())

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {}).copy()

        if instance and instance.assigned_object:
            for model_class, field in ASSIGNMENT_TYPE_TO_FIELD_MAINTENANCE.items():
                if isinstance(instance.assigned_object, model_class):
                    initial[field] = instance.assigned_object
                    break

        elif 'assigned_object_type' in initial and 'assigned_object_id' in initial:
            try:
                content_type = ContentType.objects.get(pk=initial['assigned_object_type'])
                obj = content_type.get_object_for_this_type(pk=initial['assigned_object_id'])

                for model_class, field in ASSIGNMENT_TYPE_TO_FIELD_MAINTENANCE.items():
                    if isinstance(obj, model_class):
                        initial[field] = obj.pk
                        break

            except Exception as e:
                # print(f'[Prefill error] {e}')
                pass

        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()

        selected_objects = [field for field in self.assignable_fields if self.cleaned_data.get(field)]

        if len(selected_objects) > 1:
            raise forms.ValidationError({selected_objects[1]: _('A Device/VM/Hostgroupgroup can only be assigned to a single object.')})
        elif selected_objects:
            self.instance.assigned_object = self.cleaned_data[selected_objects[0]]
        else:
            self.instance.assigned_object = None


class ZabbixMaintenanceObjectAssignmentFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixMaintenanceObjectAssignment

    zabbixmaintenance = DynamicModelChoiceField(queryset=ZabbixMaintenance.objects.all(), required=False, selector=True, label=_('Zabbix Maintenance'))

    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('zabbixmaintenance', name=_('Zabbix')),
    )

    tag = TagFilterField(model)


class ZabbixMaintenanceObjectAssignmentBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixMaintenanceObjectAssignment
    zabbixhostgroup = DynamicModelChoiceField(queryset=ZabbixHostgroup.objects.all(), required=False, selector=True, label=_('Zabbix Maintenance'))

    fieldsets = (FieldSet('zabbixmaintenance', 'value', name=_('Generic')),)
