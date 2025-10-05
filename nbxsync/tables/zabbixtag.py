import django_tables2 as tables

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixTag

__all__ = ('ZabbixTagTable',)


class ZabbixTagTable(NetBoxTable):
    name = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = ZabbixTag
        fields = (
            'pk',
            'name',
            'description',
            'tag',
            'value',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'name',
            'tag',
            'value',
        )
