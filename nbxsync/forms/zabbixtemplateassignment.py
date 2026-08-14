import logging
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet, TabbedGroups
from dcim.models import Device, VirtualDeviceContext, DeviceRole, DeviceType, Manufacturer, Platform, Site, SiteGroup, Region
from virtualization.models import Cluster, ClusterType, VirtualMachine

from nbxsync.constants.assignment_type_to_field import ASSIGNMENT_TYPE_TO_FIELD, ASSIGNMENT_TYPE_TO_FIELD_NBOBJS
from nbxsync.models import ZabbixTemplate, ZabbixTemplateAssignment, ZabbixConfigurationGroup
from nbxsync.utils import get_assigned_zabbixobjects

__all__ = ('ZabbixTemplateAssignmentForm', 'ZabbixTemplateAssignmentFilterForm')
logger = logging.getLogger(__name__)


class ZabbixTemplateAssignmentForm(NetBoxModelForm):
    zabbixtemplate = DynamicModelChoiceField(queryset=ZabbixTemplate.objects.all(), required=True, selector=True, label=_('Zabbix Template'))
    device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False, selector=True, label=_('Device'))
    virtualdevicecontext = DynamicModelChoiceField(queryset=VirtualDeviceContext.objects.all(), required=False, selector=True, label=_('Virtual Device Context'))
    devicetype = DynamicModelChoiceField(queryset=DeviceType.objects.all(), required=False, selector=True, label=_('Device Type'))
    role = DynamicModelChoiceField(queryset=DeviceRole.objects.all(), required=False, selector=True, label=_('Device Role'))
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False, selector=True, label=_('Manufacturer'))
    platform = DynamicModelChoiceField(queryset=Platform.objects.all(), required=False, selector=True, label=_('Platform'))
    virtualmachine = DynamicModelChoiceField(queryset=VirtualMachine.objects.all(), required=False, selector=True, label=_('Virtual Machine'))
    site = DynamicModelChoiceField(queryset=Site.objects.all(), required=False, selector=True, label=_('Site'))
    sitegroup = DynamicModelChoiceField(queryset=SiteGroup.objects.all(), required=False, selector=True, label=_('Site Group'))
    region = DynamicModelChoiceField(queryset=Region.objects.all(), required=False, label=_('Region'))
    cluster = DynamicModelChoiceField(queryset=Cluster.objects.all(), required=False, selector=True, label=_('Cluster'))
    clustertype = DynamicModelChoiceField(queryset=ClusterType.objects.all(), required=False, selector=True, label=_('Cluster Type'))
    zabbixconfigurationgroup = DynamicModelChoiceField(queryset=ZabbixConfigurationGroup.objects.all(), required=False, selector=True, label=_('Zabbix Configuration Group'))

    fieldsets = (
        FieldSet('zabbixtemplate', name=_('Generic')),
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
                FieldSet('zabbixconfigurationgroup', name=_('Zabbix Configuration Group')),
            ),
            name=_('Assignment'),
        ),
    )

    class Meta:
        model = ZabbixTemplateAssignment
        fields = (
            'zabbixtemplate',
            'device',
            'virtualdevicecontext',
            'virtualmachine',
            'cluster',
            'clustertype',
            'devicetype',
            'role',
            'manufacturer',
            'platform',
            'zabbixconfigurationgroup',
            'site',
            'sitegroup',
            'region',
        )

    @property
    def assignable_fields(self):
        return list(ASSIGNMENT_TYPE_TO_FIELD_NBOBJS.values())

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {}).copy()
        target = None

        if instance and instance.assigned_object:
            target = instance.assigned_object
            for model_class, field in ASSIGNMENT_TYPE_TO_FIELD.items():
                if isinstance(instance.assigned_object, model_class):
                    initial[field] = instance.assigned_object
                    break

        elif 'assigned_object_type' in initial and 'assigned_object_id' in initial:
            try:
                content_type = ContentType.objects.get(pk=initial['assigned_object_type'])
                target = content_type.get_object_for_this_type(pk=initial['assigned_object_id'])

                for model_class, field in ASSIGNMENT_TYPE_TO_FIELD.items():
                    if isinstance(target, model_class):
                        initial[field] = target.pk
                        break

            except Exception as e:
                logger.debug('Prefill error (assigned_object_type=%s, assigned_object_id=%s): %s', initial.get('assigned_object_type'), initial.get('assigned_object_id'), e)
                pass

        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

        if target is not None:
            assigned = get_assigned_zabbixobjects(target)
            excluded_ids = set()
            for assigned_template in assigned['templates']:
                excluded_ids.add(assigned_template.zabbixtemplate_id)

            if instance is not None and instance.pk and instance.zabbixtemplate_id:
                excluded_ids.discard(instance.zabbixtemplate_id)

            if excluded_ids:
                self.fields['zabbixtemplate'].queryset = ZabbixTemplate.objects.exclude(pk__in=excluded_ids)
                self.fields['zabbixtemplate'].widget.add_query_params({'id__n': list(excluded_ids)})

    def clean(self):
        super().clean()

        selected_objects = [field for field in self.assignable_fields if self.cleaned_data.get(field)]

        if len(selected_objects) > 1:
            raise forms.ValidationError({selected_objects[1]: _('A Template can only be assigned to a single object.')})
        elif selected_objects:
            self.instance.assigned_object = self.cleaned_data[selected_objects[0]]
        else:
            self.instance.assigned_object = None


class ZabbixTemplateAssignmentFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixTemplateAssignment

    zabbixtemplate = DynamicModelChoiceField(queryset=ZabbixTemplate.objects.all(), required=False, selector=True, label=_('Zabbix Template'))

    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('zabbixtemplate', name=_('Zabbix')),
    )

    tag = TagFilterField(model)
