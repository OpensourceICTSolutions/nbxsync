import logging
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet, TabbedGroups
from dcim.models import Device, VirtualDeviceContext, DeviceRole, DeviceType, Manufacturer, Platform, Site, SiteGroup, Region
from virtualization.models import Cluster, ClusterType, VirtualMachine

from nbxsync.constants import ASSIGNMENT_TYPE_TO_FIELD
from nbxsync.models import ZabbixTag, ZabbixTagAssignment, ZabbixConfigurationGroup
from nbxsync.utils import get_assigned_zabbixobjects

__all__ = ('ZabbixTagAssignmentForm', 'ZabbixTagAssignmentFilterForm', 'ZabbixTagAssignmentBulkEditForm')
logger = logging.getLogger(__name__)


class ZabbixTagAssignmentForm(NetBoxModelForm):
    zabbixtag = DynamicModelChoiceField(queryset=ZabbixTag.objects.all(), required=True, selector=True, label=_('Zabbix Tag'))
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
        FieldSet('zabbixtag', name=_('Generic')),
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
        model = ZabbixTagAssignment
        fields = (
            'zabbixtag',
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
        return list(ASSIGNMENT_TYPE_TO_FIELD.values())

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {}).copy()
        target = None

        if instance and instance.assigned_object:
            target = instance.assigned_object
            for model_class, field in ASSIGNMENT_TYPE_TO_FIELD.items():
                if isinstance(instance.assigned_object, model_class):
                    initial[field] = target
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
            for assigned_tag in assigned['tags']:
                excluded_ids.add(assigned_tag.zabbixtag_id)

            if instance is not None and instance.pk and instance.zabbixtag_id:
                excluded_ids.discard(instance.zabbixtag_id)

            if excluded_ids:
                self.fields['zabbixtag'].queryset = ZabbixTag.objects.exclude(pk__in=excluded_ids)
                self.fields['zabbixtag'].widget.add_query_params({'id__n': list(excluded_ids)})

    def clean(self):
        super().clean()

        selected_objects = [field for field in self.assignable_fields if self.cleaned_data.get(field)]

        if len(selected_objects) > 1:
            raise forms.ValidationError({selected_objects[1]: _('A Tag can only be assigned to a single object.')})
        elif selected_objects:
            self.instance.assigned_object = self.cleaned_data[selected_objects[0]]
        else:
            self.instance.assigned_object = None


class ZabbixTagAssignmentFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixTagAssignment

    zabbixtemplate = DynamicModelChoiceField(queryset=ZabbixTag.objects.all(), required=False, selector=True, label=_('Zabbix Tag'))

    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('zabbixtag', name=_('Zabbix')),
    )

    tag = TagFilterField(model)


class ZabbixTagAssignmentBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixTagAssignment

    fieldsets = (FieldSet('zabbixtag'),)
    nullable_fields = ()
