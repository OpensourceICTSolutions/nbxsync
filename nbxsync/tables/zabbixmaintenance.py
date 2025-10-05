import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixMaintenance

__all__ = ('ZabbixMaintenanceTable',)


class ZabbixMaintenanceTable(NetBoxTable):
    name = tables.Column(linkify=True)
    zabbixserver = tables.Column(linkify=True, verbose_name=_('Zabbix Server'))

    class Meta(NetBoxTable.Meta):
        model = ZabbixMaintenance
        fields = (
            'pk',
            'maintenanceid',
            'name',
            'description',
            'active_since',
            'active_till',
            'maintenance_type',
            'tags_evaltype',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'name',
            'description',
            'active_since',
            'active_till',
        )
