import django_tables2 as tables

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixTemplate

__all__ = ('ZabbixTemplateTable',)


class ZabbixTemplateTable(NetBoxTable):
    name = tables.Column(linkify=True)
    zabbixserver = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = ZabbixTemplate
        fields = (
            'pk',
            'name',
            'templateid',
            'zabbixserver',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'name',
            'zabbixserver',
        )
