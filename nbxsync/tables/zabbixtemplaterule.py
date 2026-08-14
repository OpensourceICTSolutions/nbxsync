import django_tables2 as tables
from django.utils.translation import gettext_lazy as _
from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixTemplateRule

__all__ = ('ZabbixTemplateRuleTable', 'ZabbixTemplateRuleHostgroupViewTable')


class ZabbixTemplateRuleTable(NetBoxTable):
    name = tables.Column(linkify=True)
    zabbixtemplate = tables.Column(linkify=True)
    zabbixhostgroup = tables.Column(linkify=True)
    zabbixtag = tables.Column(linkify=True)
    manufacturer = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = ZabbixTemplateRule
        fields = (
            'pk',
            'name',
            'description',
            'pattern',
            'role_pattern',
            'require_tags',
            'manufacturer',
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
            'role_pattern',
            'manufacturer',
            'zabbixtemplate',
            'zabbixhostgroup',
            'enabled',
            'priority',
        )


class ZabbixTemplateRuleHostgroupViewTable(NetBoxTable):
    """Rules that attach this hostgroup — embedded on the hostgroup detail page."""

    name = tables.Column(linkify=True)
    pattern = tables.Column()
    zabbixtemplate = tables.Column(linkify=True, verbose_name=_('Template'))
    priority = tables.Column()
    enabled = tables.BooleanColumn()

    class Meta(NetBoxTable.Meta):
        model = ZabbixTemplateRule
        fields = (
            'pk',
            'name',
            'pattern',
            'zabbixtemplate',
            'priority',
            'enabled',
        )
        default_columns = (
            'name',
            'pattern',
            'zabbixtemplate',
            'priority',
            'enabled',
        )
