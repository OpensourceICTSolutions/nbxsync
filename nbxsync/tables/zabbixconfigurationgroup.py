import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixConfigurationGroup

__all__ = ('ZabbixConfigurationGroupTable',)


class ZabbixConfigurationGroupTable(NetBoxTable):
    name = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = ZabbixConfigurationGroup
        fields = (
            'pk',
            'name',
            'description',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'name',
            'description',
        )
