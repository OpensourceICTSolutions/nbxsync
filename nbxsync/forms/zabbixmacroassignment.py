import logging
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet, TabbedGroups
from dcim.models import Device, VirtualDeviceContext, DeviceRole, DeviceType, Manufacturer, Platform
from virtualization.models import Cluster, ClusterType, VirtualMachine

from nbxsync.constants import ASSIGNMENT_TYPE_TO_FIELD
from nbxsync.models import ZabbixMacro, ZabbixMacroAssignment

__all__ = ('ZabbixMacroAssignmentForm', 'ZabbixMacroAssignmentFilterForm', 'ZabbixMacroAssignmentBulkEditForm')
logger = logging.getLogger(__name__)


class ZabbixMacroAssignmentForm(NetBoxModelForm):
    zabbixmacro = DynamicModelChoiceField(queryset=ZabbixMacro.objects.all(), required=True, selector=True, label=_('Zabbix Macro'))
    value = forms.CharField(label=_('Value'), max_length=2048, required=False)
    device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False, selector=True, label=_('Device'))
    virtualdevicecontext = DynamicModelChoiceField(queryset=VirtualDeviceContext.objects.all(), required=False, selector=True, label=_('Virtual Device Context'))
    devicetype = DynamicModelChoiceField(queryset=DeviceType.objects.all(), required=False, selector=True, label=_('Device Type'))
    role = DynamicModelChoiceField(queryset=DeviceRole.objects.all(), required=False, selector=True, label=_('Device Role'))
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False, selector=True, label=_('Manufacturer'))
    platform = DynamicModelChoiceField(queryset=Platform.objects.all(), required=False, selector=True, label=_('Platform'))
    virtualmachine = DynamicModelChoiceField(queryset=VirtualMachine.objects.all(), required=False, selector=True, label=_('Virtual Machine'))
    cluster = DynamicModelChoiceField(queryset=Cluster.objects.all(), required=False, selector=True, label=_('Cluster'))
    clustertype = DynamicModelChoiceField(queryset=ClusterType.objects.all(), required=False, selector=True, label=_('Cluster Type'))

    fieldsets = (
        FieldSet('zabbixmacro', 'is_regex', 'context', 'value', name=_('Generic')),
        FieldSet(
            TabbedGroups(
                FieldSet('device', name=_('Device')),
                FieldSet('virtualdevicecontext', name=_('Virtual Device Context')),
                FieldSet('devicetype', name=_('Device Type')),
                FieldSet('role', name=_('Device Role')),
                FieldSet('manufacturer', name=_('Manufacturer')),
                FieldSet('platform', name=_('Platform')),
                FieldSet('virtualmachine', name=_('Virtual Machine')),
                FieldSet('cluster', name=_('Cluster')),
                FieldSet('clustertype', name=_('Cluster Type')),
            ),
            name=_('Assignment'),
        ),
    )

    class Meta:
        model = ZabbixMacroAssignment
        fields = (
            'zabbixmacro',
            'is_regex',
            'context',
            'value',
            'device',
            'virtualdevicecontext',
            'virtualmachine',
            'cluster',
            'clustertype',
            'devicetype',
            'role',
            'manufacturer',
            'platform',
        )

    @property
    def assignable_fields(self):
        return list(ASSIGNMENT_TYPE_TO_FIELD.values())

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
            raise forms.ValidationError({selected_objects[1]: _('A Macro can only be assigned to a single object.')})
        elif selected_objects:
            self.instance.assigned_object = self.cleaned_data[selected_objects[0]]
        else:
            self.instance.assigned_object = None


class ZabbixMacroAssignmentFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixMacroAssignment

    zabbixmacro = DynamicModelChoiceField(queryset=ZabbixMacro.objects.all(), required=False, selector=True, label=_('Zabbix Macro'))

    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('zabbixmacro', 'value', name=_('Zabbix')),
    )

    tag = TagFilterField(model)


class ZabbixMacroAssignmentBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixMacroAssignment
    zabbixmacro = DynamicModelChoiceField(queryset=ZabbixMacro.objects.all(), required=False, selector=True, label=_('Zabbix Macro'))
    value = forms.CharField(label=_('Value'), max_length=2048, required=False)
    context = forms.CharField(label=_('Context'), max_length=2048, required=False)

    fieldsets = (FieldSet('zabbixmacro', 'value', 'context'),)
    nullable_fields = ()
