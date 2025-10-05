from django import forms
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelImportForm, NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, TagFilterField, CSVModelChoiceField
from utilities.forms.rendering import FieldSet

from nbxsync.models import ZabbixHostgroup, ZabbixServer

__all__ = ('ZabbixHostgroupForm', 'ZabbixHostgroupFilterForm', 'ZabbixHostgroupBulkEditForm', 'ZabbixHostgroupBulkImportForm')


class ZabbixHostgroupForm(NetBoxModelForm):
    name = forms.CharField(label=_('Name'), max_length=200, required=True)
    value = forms.CharField(label=_('Value'), max_length=200, required=True)
    groupid = forms.IntegerField(label=_('Host Hostgroup ID'), required=False)
    description = forms.CharField(label=_('Description'), required=False, widget=forms.Textarea(attrs={'rows': 1, 'cols': 40}))
    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=True, selector=True, label=_('Zabbix Server'))

    fieldsets = (FieldSet('name', 'description', 'value', 'groupid', 'zabbixserver'),)

    class Meta:
        model = ZabbixHostgroup
        fields = (
            'name',
            'description',
            'groupid',
            'value',
            'zabbixserver',
        )


class ZabbixHostgroupFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixHostgroup

    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=False, selector=True, label=_('Zabbix Server'))

    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('name', 'description', 'value', 'groupid', 'zabbixserver', name=_('Zabbix Hostgroup')),
    )

    tag = TagFilterField(model)


class ZabbixHostgroupBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixHostgroup

    name = forms.CharField(label=_('Name'), max_length=200, required=False)
    value = forms.CharField(label=_('Value'), max_length=200, required=False)
    groupid = forms.IntegerField(label=_('Host Hostgroup ID'), required=False)
    description = forms.CharField(label=_('Description'), required=False, widget=forms.Textarea(attrs={'rows': 1, 'cols': 40}))
    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=False, selector=True, label=_('Zabbix Server'))

    fieldsets = (FieldSet('name', 'description', 'value', 'groupid', 'zabbixserver'),)
    nullable_fields = ()


class ZabbixHostgroupBulkImportForm(NetBoxModelImportForm):
    zabbixserver = CSVModelChoiceField(queryset=ZabbixServer.objects.all(), to_field_name='name', help_text=_('Assigned Zabbix Server'))

    class Meta:
        model = ZabbixHostgroup
        fields = (
            'name',
            'value',
            'groupid',
            'description',
            'zabbixserver',
        )
