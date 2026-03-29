import django_tables2 as tables

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixServer

__all__ = ('ZabbixServerTable',)


class ZabbixServerTable(NetBoxTable):
    name = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = ZabbixServer
        fields = (
            'pk',
            'name',
            'description',
            'sync_enabled',
            'skip_version_check',
            'url',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'name',
            'url',
            'sync_enabled',
            'skip_version_check',
        )
