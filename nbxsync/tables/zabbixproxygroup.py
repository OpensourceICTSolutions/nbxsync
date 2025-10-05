import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixProxyGroup

__all__ = ('ZabbixProxyGroupTable',)


class ZabbixProxyGroupTable(NetBoxTable):
    name = tables.Column(linkify=True)
    zabbixserver = tables.Column(linkify=True, verbose_name=_('Zabbix Server'))
    min_online = tables.Column(verbose_name=_('Min Online'))
    failover_delay = tables.Column(verbose_name=_('Failover Delay'))
    state = tables.Column(verbose_name=_('State'))

    class Meta(NetBoxTable.Meta):
        model = ZabbixProxyGroup
        fields = (
            'pk',
            'name',
            'description',
            'min_online',
            'failover_delay',
            'zabbixserver',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'name',
            'zabbixserver',
            'min_online',
            'failover_delay',
        )
