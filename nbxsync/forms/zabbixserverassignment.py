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
from nbxsync.models import ZabbixProxy, ZabbixProxyGroup, ZabbixServer, ZabbixServerAssignment, ZabbixConfigurationGroup

__all__ = ('ZabbixServerAssignmentForm', 'ZabbixServerAssignmentFilterForm', 'ZabbixServerAssignmentBulkImportForm', 'ZabbixServerAssignmentBulkEditForm')
logger = logging.getLogger(__name__)


class ZabbixServerAssignmentForm(NetBoxModelForm):
    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=True, selector=True, label=_('Zabbix Server'))
    zabbixproxy = DynamicModelChoiceField(queryset=ZabbixProxy.objects.all(), required=False, selector=True, label=_('Zabbix Proxy'))
    zabbixproxygroup = DynamicModelChoiceField(queryset=ZabbixProxyGroup.objects.all(), required=False, selector=True, label=_('Zabbix Proxygroup'))
    zabbixconfigurationgroup = DynamicModelChoiceField(queryset=ZabbixConfigurationGroup.objects.all(), required=False, selector=True, label=_('Zabbix Configuration Group'))

    device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False, selector=True, label=_('Device'))
    virtualdevicecontext = DynamicModelChoiceField(queryset=VirtualDeviceContext.objects.all(), required=False, selector=True, label=_('Virtual Device Context'))
    virtualmachine = DynamicModelChoiceField(queryset=VirtualMachine.objects.all(), required=False, selector=True, label=_('Virtual Machine'))

    fieldsets = (
        FieldSet('zabbixserver', name=_('Generic')),
        FieldSet(
            TabbedGroups(
                FieldSet('zabbixproxy', name=_('Proxy')),
                FieldSet('zabbixproxygroup', name=_('Proxy Group')),
            ),
            name=_('Proxy Assignment'),
        ),
        FieldSet(
            TabbedGroups(
                FieldSet('device', name=_('Device')),
                FieldSet('virtualdevicecontext', name=_('Virtual Device Context')),
                FieldSet('virtualmachine', name=_('Virtual Machine')),
                FieldSet('zabbixconfigurationgroup', name=_('Zabbix Configuration Group')),
            ),
            name=_('Device Assignment'),
        ),
    )

    class Meta:
        model = ZabbixServerAssignment
        fields = (
            'zabbixserver',
            'zabbixproxy',
            'zabbixproxygroup',
            'device',
            'virtualdevicecontext',
            'virtualmachine',
            'zabbixconfigurationgroup',
        )

    @property
    def assignable_fields(self):
        return list(ASSIGNMENT_TYPE_TO_FIELD_NBOBJS.values())

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
            raise forms.ValidationError({selected_objects[1]: _('A ZabbixServer can only be assigned to a single object.')})
        elif selected_objects:
            self.instance.assigned_object = self.cleaned_data[selected_objects[0]]
        else:
            self.instance.assigned_object = None


class ZabbixServerAssignmentFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixServerAssignment

    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=True, selector=True, label=_('Zabbix Server'))
    zabbixproxy = DynamicModelChoiceField(queryset=ZabbixProxy.objects.all(), required=True, selector=True, label=_('Zabbix Proxy'))
    zabbixproxygroup = DynamicModelChoiceField(queryset=ZabbixProxyGroup.objects.all(), required=True, selector=True, label=_('Zabbix Proxygroup'))

    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('zabbixserver', 'zabbixproxy', 'zabbixproxygroup', name=_('Zabbix')),
    )

    tag = TagFilterField(model)


class ZabbixServerAssignmentBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixServerAssignment
    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=False, selector=True, label=_('Zabbix Server'))
    zabbixproxy = DynamicModelChoiceField(queryset=ZabbixProxy.objects.all(), required=False, selector=True, label=_('Zabbix Proxy'))
    zabbixproxygroup = DynamicModelChoiceField(queryset=ZabbixProxyGroup.objects.all(), required=False, selector=True, label=_('Zabbix Proxygroup'))

    fieldsets = (FieldSet('zabbixserver', 'zabbixproxy', 'zabbixproxygroup'),)
    nullable_fields = ()


class ZabbixServerAssignmentBulkImportForm(NetBoxModelImportForm):
    zabbixserver = CSVModelChoiceField(queryset=ZabbixServer.objects.all(), to_field_name='name', help_text=_('Assigned Zabbix Server'))
    zabbixproxy = CSVModelChoiceField(queryset=ZabbixProxy.objects.all(), to_field_name='name', help_text=_('Assigned Zabbix Proxy'))
    zabbixproxygroup = CSVModelChoiceField(queryset=ZabbixProxyGroup.objects.all(), to_field_name='name', help_text=_('Assigned Zabbix Proxy Group'))

    class Meta:
        model = ZabbixServerAssignment
        fields = (
            'zabbixserver',
            'zabbixproxy',
            'zabbixproxygroup',
        )
