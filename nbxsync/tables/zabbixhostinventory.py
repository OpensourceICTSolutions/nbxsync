import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixHostInventory
from nbxsync.tables.columns import ContentTypeModelNameColumn

__all__ = ('ZabbixHostInventoryTable',)


class ZabbixHostInventoryTable(NetBoxTable):
    assigned_object = tables.Column(verbose_name=_('Object'), linkify=True, orderable=False)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))

    class Meta(NetBoxTable.Meta):
        model = ZabbixHostInventory
        fields = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'assigned_object_type',
            'assigned_object',
        )
