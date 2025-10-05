from django import forms
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet

from nbxsync.models import ZabbixProxyGroup, ZabbixServer


__all__ = ('ZabbixProxyGroupForm', 'ZabbixProxyGroupFilterForm', 'ZabbixProxyGroupBulkEditForm')


class ZabbixProxyGroupForm(NetBoxModelForm):
    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=True, selector=True, label=_('Zabbix Server'))
    name = forms.CharField(required=True, label=_('Name'))
    description = forms.CharField(label=_('Description'), required=False, widget=forms.Textarea(attrs={'rows': 1, 'cols': 40}))
    failover_delay = forms.CharField(required=False, label=_('Vendor'))
    min_online = forms.IntegerField(required=False, label=_('Minimum online proxies'))

    class Meta:
        model = ZabbixProxyGroup
        fields = (
            'name',
            'zabbixserver',
            'description',
            'min_online',
            'failover_delay',
        )


class ZabbixProxyGroupFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixProxyGroup

    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=True, selector=True, label=_('Zabbix Server'))

    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('name', 'zabbixserver', 'min_online', 'failover_delay', name=_('Zabbix Proxy Group')),
    )

    tag = TagFilterField(model)


class ZabbixProxyGroupBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixProxyGroup

    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=False, selector=True, label=_('Zabbix Server'))
    name = forms.CharField(required=False, label=_('Name'))
    description = forms.CharField(label=_('Description'), required=False, widget=forms.Textarea(attrs={'rows': 1, 'cols': 40}))
    failover_delay = forms.CharField(required=False, label=_('Vendor'))
    min_online = forms.IntegerField(required=False, label=_('Minimum online proxies'))

    fieldsets = (
        FieldSet(
            'name',
            'zabbixserver',
            'description',
            'min_online',
            'failover_delay',
        ),
    )

    nullable_fields = 'description'
