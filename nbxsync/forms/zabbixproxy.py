from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet

from nbxsync.choices import *
from nbxsync.forms import MultiIPWidget
from nbxsync.forms.fields import MultiIPField
from nbxsync.models import ZabbixProxy, ZabbixProxyGroup, ZabbixServer
from nbxsync.models.zabbixproxy import default_tls_accept

__all__ = ('ZabbixProxyForm', 'ZabbixProxyFilterForm', 'ZabbixProxyBulkEditForm')


class ZabbixProxyForm(NetBoxModelForm):
    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=True, selector=False, label=_('Zabbix Server'))
    proxygroup = DynamicModelChoiceField(queryset=ZabbixProxyGroup.objects.all(), required=False, selector=True, label=_('Proxy Group'), query_params={'zabbixserver_id': '$zabbixserver'})
    local_port = forms.IntegerField(initial=10051, required=False, validators=[MinValueValidator(0), MaxValueValidator(65535)], help_text='Enter a valid IP port number (0-65535)')
    description = forms.CharField(label=_('Description'), required=False, widget=forms.Textarea(attrs={'rows': 1, 'cols': 40}))
    allowed_addresses = MultiIPField(required=False, widget=MultiIPWidget(), help_text='Enter one or more IP addresses')
    tls_connect = forms.TypedChoiceField(choices=ZabbixTLSChoices, required=False, coerce=int, label=_('Connections to proxy'))
    tls_accept = forms.TypedMultipleChoiceField(choices=ZabbixTLSChoices, required=False, coerce=int, initial=default_tls_accept, label=_('Connections from proxy'))
    tls_psk_identity = forms.CharField(required=False, label=_('PSK identity'))
    tls_psk = forms.CharField(required=False, label=_('PSK'), widget=forms.PasswordInput(render_value=True))
    tls_issuer = forms.CharField(required=False, label=_('Issuer'))
    tls_subject = forms.CharField(required=False, label=_('Subject'))
    timeout_zabbix_agent = forms.CharField(required=False, label=_('Zabbix agent'))
    timeout_simple_check = forms.CharField(required=False, label=_('Simple check'))
    timeout_snmp_agent = forms.CharField(required=False, label=_('SNMP agent'))
    timeout_external_check = forms.CharField(required=False, label=_('External check'))
    timeout_db_monitor = forms.CharField(required=False, label=_('Database monitor'))
    timeout_http_agent = forms.CharField(required=False, label=_('HTTP agent'))
    timeout_ssh_agent = forms.CharField(required=False, label=_('SSH agent'))
    timeout_telnet_agent = forms.CharField(required=False, label=_('TELNET agent'))
    timeout_script = forms.CharField(required=False, label=_('Script'))
    timeout_browser = forms.CharField(required=False, label=_('Browser'))

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Force update of allowed_addresses even if empty
        instance.allowed_addresses = self.cleaned_data.get('allowed_addresses', [])

        if commit:
            instance.save()
            self._save_m2m()

        return instance

    class Meta:
        model = ZabbixProxy
        fields = (
            'name',
            'description',
            'zabbixserver',
            'proxygroup',
            'operating_mode',
            'address',
            'port',
            'allowed_addresses',
            'local_address',
            'local_port',
            'tls_connect',
            'tls_accept',
            'tls_psk_identity',
            'tls_psk',
            'tls_issuer',
            'tls_subject',
            'custom_timeouts',
            'timeout_zabbix_agent',
            'timeout_simple_check',
            'timeout_snmp_agent',
            'timeout_external_check',
            'timeout_db_monitor',
            'timeout_http_agent',
            'timeout_ssh_agent',
            'timeout_telnet_agent',
            'timeout_script',
            'timeout_browser',
        )


class ZabbixProxyFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixProxy

    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=False, selector=True, label=_('Zabbix Server'))
    proxygroup = DynamicModelChoiceField(queryset=ZabbixProxyGroup.objects.all(), required=False, selector=True, label=_('Proxy Group'), query_params={'zabbixserver_id': '$zabbixserver'})
    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet(
            'name',
            'address',
            'port',
            'zabbixserver',
            'proxygroup',
            'operating_mode',
            'tls_connect',
            'tls_accept',
            name=_('Zabbix Proxy'),
        ),
    )

    tag = TagFilterField(model)


class ZabbixProxyBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixProxy

    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=False, selector=True, label=_('Zabbix Server'))
    proxygroup = DynamicModelChoiceField(queryset=ZabbixProxyGroup.objects.all(), required=False, selector=True, label=_('Proxy Group'), query_params={'zabbixserver_id': '$zabbixserver'})
    fieldsets = (
        FieldSet(
            'name',
            'zabbixserver',
            'proxygroup',
            'operating_mode',
            'address',
            'port',
            'local_address',
            'local_port',
            'tls_connect',
            'tls_accept',
            'tls_psk_identity',
            'tls_psk',
            'tls_issuer',
            'tls_subject',
            'custom_timeouts',
            'timeout_zabbix_agent',
            'timeout_simple_check',
            'timeout_snmp_agent',
            'timeout_external_check',
            'timeout_db_monitor',
            'timeout_http_agent',
            'timeout_ssh_agent',
            'timeout_telnet_agent',
            'timeout_script',
            'timeout_browser',
            'description',
        ),
    )
    nullable_fields = (
        'description',
        'proxygroup',
        'address',
        'local_address',
        'tls_psk_identity',
        'tls_psk',
        'tls_issuer',
        'tls_subject',
    )
