import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixProxy

__all__ = ('ZabbixProxyTable', 'ZabbixProxyObjectViewTable')


class ZabbixProxyTable(NetBoxTable):
    name = tables.Column(linkify=True)
    operating_mode = tables.Column(verbose_name=_('Mode'))
    zabbixserver = tables.Column(linkify=True, verbose_name=_('Zabbix Server'))
    proxygroup = tables.Column(verbose_name=_('Proxy Group'), linkify=True)

    class Meta(NetBoxTable.Meta):
        model = ZabbixProxy
        fields = (
            'pk',
            'name',
            'zabbixserver',
            'proxygroup',
            'operating_mode',
            'address',
            'port',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'name',
            'zabbixserver',
            'proxygroup',
            'operating_mode',
            'address',
            'port',
        )


class ZabbixProxyObjectViewTable(NetBoxTable):
    name = tables.Column(linkify=True)
    operating_mode = tables.Column(verbose_name=_('Mode'))
    zabbixserver = tables.Column(linkify=True, verbose_name=_('Zabbix Server'))
    proxygroup = tables.Column(verbose_name=_('Proxy Group'), linkify=True)

    class Meta(NetBoxTable.Meta):
        model = ZabbixProxy
        fields = (
            'name',
            'operating_mode',
            'zabbixserver',
            'proxygroup',
            'address',
            'port',
        )
        default_columns = (
            'name',
            'operating_mode',
            'address',
            'port',
        )
