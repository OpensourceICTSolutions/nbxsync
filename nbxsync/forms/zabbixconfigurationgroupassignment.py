import logging
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _


from netbox.forms import NetBoxModelImportForm, NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, TagFilterField, CSVModelChoiceField
from utilities.forms.rendering import FieldSet, TabbedGroups
from dcim.models import Device, VirtualDeviceContext, DeviceRole, DeviceType, Manufacturer, Platform, Site, SiteGroup, Region
from extras.models import Tag
from virtualization.models import Cluster, ClusterType, VirtualMachine

from nbxsync.constants.assignment_type_to_field import ASSIGNMENT_TYPE_TO_FIELD, ASSIGNMENT_TYPE_TO_FIELD_NBOBJS
from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment

__all__ = ('ZabbixConfigurationGroupAssignmentForm', 'ZabbixConfigurationGroupAssignmentFilterForm', 'ZabbixConfigurationGroupAssignmentBulkImportForm', 'ZabbixConfigurationGroupAssignmentBulkEditForm')
logger = logging.getLogger(__name__)


class ZabbixConfigurationGroupAssignmentForm(NetBoxModelForm):
    zabbixconfigurationgroup = DynamicModelChoiceField(queryset=ZabbixConfigurationGroup.objects.all(), required=True, selector=True, label=_('Zabbix Configuration Group'))

    device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False, selector=True, label=_('Device'))
    virtualdevicecontext = DynamicModelChoiceField(queryset=VirtualDeviceContext.objects.all(), required=False, selector=True, label=_('Virtual Device Context'))
    devicetype = DynamicModelChoiceField(queryset=DeviceType.objects.all(), required=False, selector=True, label=_('Device Type'))
    role = DynamicModelChoiceField(queryset=DeviceRole.objects.all(), required=False, selector=True, label=_('Device Role'))
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False, selector=True, label=_('Manufacturer'))
    platform = DynamicModelChoiceField(queryset=Platform.objects.all(), required=False, selector=True, label=_('Platform'))
    virtualmachine = DynamicModelChoiceField(queryset=VirtualMachine.objects.all(), required=False, selector=True, label=_('Virtual Machine'))
    cluster = DynamicModelChoiceField(queryset=Cluster.objects.all(), required=False, selector=True, label=_('Cluster'))
    clustertype = DynamicModelChoiceField(queryset=ClusterType.objects.all(), required=False, selector=True, label=_('Cluster Type'))
    site = DynamicModelChoiceField(queryset=Site.objects.all(), required=False, selector=True, label=_('Site'))
    sitegroup = DynamicModelChoiceField(queryset=SiteGroup.objects.all(), required=False, selector=True, label=_('Site Group'))
    region = DynamicModelChoiceField(queryset=Region.objects.all(), required=False, label=_('Region'))
    tag = DynamicModelChoiceField(queryset=Tag.objects.all(), required=False, selector=True, label=_('Tag'))

    fieldsets = (
        FieldSet('zabbixconfigurationgroup', name=_('Generic')),
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
                FieldSet('site', name=_('Site')),
                FieldSet('sitegroup', name=_('Site Group')),
                FieldSet('region', name=_('Region')),
                FieldSet('tag', name=_('Tag')),
            ),
            name=_('Assignment'),
        ),
    )

    class Meta:
        model = ZabbixConfigurationGroupAssignment
        fields = (
            'zabbixconfigurationgroup',
            'device',
            'virtualdevicecontext',
            'virtualmachine',
            'cluster',
            'clustertype',
            'devicetype',
            'role',
            'manufacturer',
            'platform',
            'site',
            'sitegroup',
            'region',
            'tag',
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
            raise forms.ValidationError(_('A Zabbix Configuration Group must be assigned to an object.'))


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
