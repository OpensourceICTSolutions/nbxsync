import django_tables2 as tables
from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixTemplateRule

__all__ = ('ZabbixTemplateRuleTable',)


class ZabbixTemplateRuleTable(NetBoxTable):
    name = tables.Column(linkify=True)
    zabbixtemplate = tables.Column(linkify=True)
    zabbixhostgroup = tables.Column(linkify=True)
    zabbixtag = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = ZabbixTemplateRule
        fields = (
            'pk',
            'name',
            'description',
            'pattern',
            'zabbixtemplate',
            'zabbixhostgroup',
            'zabbixtag',
            'enabled',
            'priority',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'name',
            'pattern',
            'zabbixtemplate',
            'zabbixhostgroup',
            'enabled',
            'priority',
        )
