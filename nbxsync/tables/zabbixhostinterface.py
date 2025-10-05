import django_tables2 as tables
from django.utils.translation import gettext as _

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixHostInterface
from nbxsync.tables.columns import ContentTypeModelNameColumn

__all__ = ('ZabbixHostInterfaceTable', 'ZabbixHostInterfaceObjectViewTable')


class ZabbixHostInterfaceTable(NetBoxTable):
    zabbixserver = tables.Column(linkify=True)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))
    assigned_object = tables.Column(verbose_name=_('Object'), linkify=True, orderable=False)
    type = tables.Column(accessor='get_type_display', verbose_name=_('Host interface type'))
    interface_type = tables.Column(accessor='get_interface_type_display')
    ip = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = ZabbixHostInterface
        fields = (
            'zabbixserver',
            'assigned_object_type',
            'assigned_object',
            'type',
            'dns',
            'ip',
            'port',
            'useip',
            'interface_type',
        )
        default_columns = (
            'zabbixserver',
            'assigned_object',
            'type',
            'ip',
            'port',
        )


class ZabbixHostInterfaceObjectViewTable(NetBoxTable):
    zabbixserver = tables.Column(linkify=True)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))
    assigned_object = tables.Column(verbose_name=_('Object'), linkify=True, orderable=False)
    type = tables.Column(accessor='get_type_display')
    interface_type = tables.Column(accessor='get_interface_type_display')
    ip = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = ZabbixHostInterface
        fields = (
            'zabbixserver',
            'assigned_object_type',
            'assigned_object',
            'type',
            'dns',
            'ip',
            'port',
            'useip',
            'interface_type',
        )
        default_columns = (
            'zabbixserver',
            'type',
        )
