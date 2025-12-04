import logging
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _


from netbox.forms import NetBoxModelImportForm, NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, TagFilterField, CSVModelChoiceField
from utilities.forms.rendering import FieldSet, TabbedGroups
from dcim.models import Device, VirtualDeviceContext
from virtualization.models import VirtualMachine

from nbxsync.constants import ASSIGNMENT_TYPE_TO_FIELD, ASSIGNMENT_TYPE_TO_FIELD_NBOBJS
from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment

__all__ = ('ZabbixConfigurationGroupAssignmentForm', 'ZabbixConfigurationGroupAssignmentFilterForm', 'ZabbixConfigurationGroupAssignmentBulkImportForm', 'ZabbixConfigurationGroupAssignmentBulkEditForm')
logger = logging.getLogger(__name__)


class ZabbixConfigurationGroupAssignmentForm(NetBoxModelForm):
    zabbixconfigurationgroup = DynamicModelChoiceField(queryset=ZabbixConfigurationGroup.objects.all(), required=True, selector=True, label=_('Zabbix Configuration Group'))

    device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False, selector=True, label=_('Device'))
    virtualdevicecontext = DynamicModelChoiceField(queryset=VirtualDeviceContext.objects.all(), required=False, selector=True, label=_('Virtual Device Context'))
    virtualmachine = DynamicModelChoiceField(queryset=VirtualMachine.objects.all(), required=False, selector=True, label=_('Virtual Machine'))

    fieldsets = (
        FieldSet('zabbixconfigurationgroup', name=_('Generic')),
        FieldSet(
            TabbedGroups(
                FieldSet('device', name=_('Device')),
                FieldSet('virtualdevicecontext', name=_('Virtual Device Context')),
                FieldSet('virtualmachine', name=_('Virtual Machine')),
            ),
            name=_('Device Assignment'),
        ),
    )

    class Meta:
        model = ZabbixConfigurationGroupAssignment
        fields = (
            'zabbixconfigurationgroup',
            'device',
            'virtualdevicecontext',
            'virtualmachine',
        )

    @property
    def assignable_fields(self):
        return [value for value in ASSIGNMENT_TYPE_TO_FIELD_NBOBJS.values() if value != 'zabbixconfigurationgroup']

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {}).copy()

        if instance and instance.assigned_object:
            for model_class, field in ASSIGNMENT_TYPE_TO_FIELD.items():
                if isinstance(instance.assigned_object, model_class):
                    initial[field] = instance.assigned_object
                    break

        elif 'assigned_object_type' in initial and 'assigned_object_id' in initial:
            try:
                content_type = ContentType.objects.get(pk=initial['assigned_object_type'])
                obj = content_type.get_object_for_this_type(pk=initial['assigned_object_id'])

                for model_class, field in ASSIGNMENT_TYPE_TO_FIELD.items():
                    if isinstance(obj, model_class):
                        initial[field] = obj.pk
                        break

            except Exception as e:
                logger.debug('Prefill error (assigned_object_type=%s, assigned_object_id=%s): %s', initial.get('assigned_object_type'), initial.get('assigned_object_id'), e)
                pass

        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()

        selected_objects = [field for field in self.assignable_fields if self.cleaned_data.get(field)]

        if len(selected_objects) > 1:
            raise forms.ValidationError({selected_objects[1]: _(f'A Zabbix Configuration Group can only be assigned to a single object.')})
        elif selected_objects:
            self.instance.assigned_object = self.cleaned_data[selected_objects[0]]
        else:
            self.instance.assigned_object = None


class ZabbixConfigurationGroupAssignmentFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixConfigurationGroupAssignment

    zabbixconfigurationgroup = DynamicModelChoiceField(queryset=ZabbixConfigurationGroup.objects.all(), required=True, selector=True, label=_('Zabbix Configuration Group'))

    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('zabbixconfigurationgroup', name=_('Zabbix Configuration Group')),
    )

    tag = TagFilterField(model)


class ZabbixConfigurationGroupAssignmentBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixConfigurationGroupAssignment
    zabbixconfigurationgroup = DynamicModelChoiceField(queryset=ZabbixConfigurationGroup.objects.all(), required=False, selector=True, label=_('Zabbix Configuration Group'))

    fieldsets = (FieldSet('zabbixconfigurationgroup'),)
    nullable_fields = ()


class ZabbixConfigurationGroupAssignmentBulkImportForm(NetBoxModelImportForm):
    zabbixconfigurationgroup = CSVModelChoiceField(queryset=ZabbixConfigurationGroup.objects.all(), to_field_name='name', help_text=_('Assigned Zabbix Configuration Group'))

    class Meta:
        model = ZabbixConfigurationGroupAssignment
        fields = ('zabbixconfigurationgroup',)
