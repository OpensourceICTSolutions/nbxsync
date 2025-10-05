import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment
from nbxsync.tables import ZabbixInheritedAssignmentTable
from nbxsync.tables.columns import ContentTypeModelNameColumn

__all__ = ('ZabbixHostgroupTable', 'ZabbixHostgroupObjectViewTable')


class ZabbixHostgroupTable(NetBoxTable):
    name = tables.Column(linkify=True)
    zabbixserver = tables.Column(linkify=True, verbose_name=_('Zabbix Server'))

    class Meta(NetBoxTable.Meta):
        model = ZabbixHostgroup
        fields = (
            'pk',
            'groupid',
            'name',
            'description',
            'value',
            'zabbixserver',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'name',
            'description',
            'value',
            'zabbixserver',
        )


class ZabbixHostgroupObjectViewTable(ZabbixInheritedAssignmentTable, NetBoxTable):
    name = tables.Column(linkify=True)
    assigned_object = tables.Column(verbose_name=_('Assigned To'), linkify=True, orderable=False)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))

    rendered_output = tables.TemplateColumn(
        template_code="""
        {% load zabbix_hostgroups %}
        {% render_zabbix_hostgroup_assignment record as rendered_output %}
        {{ rendered_output|escape }}
        """,
        verbose_name='Value',
    )

    class Meta(NetBoxTable.Meta):
        model = ZabbixHostgroupAssignment
        fields = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'inherited_from',
            'created',
            'last_updated',
            'rendered_output',
        )
        default_columns = ('pk', 'assigned_object_type', 'assigned_object', 'rendered_output', 'inherited_from')
