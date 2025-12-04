import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixMacro
from nbxsync.tables.columns import ContentTypeModelNameColumn

__all__ = ('ZabbixMacroTable',)


class ZabbixMacroTable(NetBoxTable):
    macro = tables.Column(linkify=True)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))
    assigned_object = tables.Column(verbose_name=_('Object'), linkify=True, orderable=False)
    hostmacroid = tables.Column(verbose_name=_('Host Macro ID'))

    class Meta(NetBoxTable.Meta):
        model = ZabbixMacro
        fields = (
            'pk',
            'hostmacroid',
            'macro',
            'value',
            'description',
            'type',
            'assigned_object_type',
            'assigned_object',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'macro',
            'value',
            'description',
            'assigned_object_type',
            'assigned_object',
        )
