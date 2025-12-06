from django import forms
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet

from nbxsync.choices import ZabbixMaintenanceTagOperatorChoices
from nbxsync.models import ZabbixMaintenance, ZabbixMaintenanceTagAssignment, ZabbixTag

__all__ = ('ZabbixMaintenanceTagAssignmentForm', 'ZabbixMaintenanceTagAssignmentFilterForm', 'ZabbixMaintenanceTagAssignmentBulkEditForm')


class ZabbixMaintenanceTagAssignmentForm(NetBoxModelForm):
    zabbixmaintenance = DynamicModelChoiceField(queryset=ZabbixMaintenance.objects.all(), required=True, selector=True, label=_('Zabbix Maintenance'))
    zabbixtag = DynamicModelChoiceField(queryset=ZabbixTag.objects.all(), required=True, selector=True, query_params={'is_template': False}, label=_('Zabbix Tag'), help_text=_('Static only, no templated Zabbix Tags'))
    operator = forms.TypedChoiceField(choices=ZabbixMaintenanceTagOperatorChoices, required=True, coerce=int, label=_('Operator'))
    value = forms.CharField(required=False, label=_('Value'))

    fieldsets = (
        FieldSet('zabbixmaintenance', name=_('Generic')),
        FieldSet('zabbixtag', 'operator', 'value', name=_('Zabbix Tag')),
    )

    class Meta:
        model = ZabbixMaintenanceTagAssignment
        fields = (
            'zabbixmaintenance',
            'zabbixtag',
            'operator',
            'value',
        )


class ZabbixMaintenanceTagAssignmentFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixMaintenanceTagAssignment

    zabbixmaintenance = DynamicModelChoiceField(queryset=ZabbixMaintenance.objects.all(), required=False, selector=True, label=_('Zabbix Maintenance'))

    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('zabbixmaintenance', name=_('Zabbix')),
    )

    tag = TagFilterField(model)


class ZabbixMaintenanceTagAssignmentBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixMaintenanceTagAssignment
    zabbixtag = DynamicModelChoiceField(queryset=ZabbixTag.objects.all(), required=False, selector=True, label=_('Zabbix Tag'))

    fieldsets = (FieldSet('zabbixmaintenance', 'value', name=_('Generic')),)
