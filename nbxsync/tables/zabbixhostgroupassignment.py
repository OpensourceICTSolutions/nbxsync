import django_tables2 as tables
from django.utils.translation import gettext_lazy as _
from django_tables2.utils import A

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixHostgroupAssignment
from nbxsync.tables import ZabbixInheritedAssignmentTable
from nbxsync.tables.columns import ContentTypeModelNameColumn, InheritanceAwareActionsColumn

__all__ = ('ZabbixHostgroupAssignmentTable', 'ZabbixHostgroupAssignmentObjectViewTable')


class ZabbixHostgroupAssignmentTable(ZabbixInheritedAssignmentTable, NetBoxTable):
    name = tables.Column(linkify=True)
    assigned_object = tables.Column(verbose_name=_('Assigned To'), linkify=True, orderable=False)
    zabbixhostgroup = tables.Column(accessor='zabbixhostgroup.name', verbose_name=_('Zabbix Hostgroup'), linkify={'viewname': 'plugins:nbxsync:zabbixhostgroup', 'args': [A('zabbixhostgroup.pk')]})
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))
    actions = InheritanceAwareActionsColumn()

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
            'zabbixhostgroup',
            'inherited_from',
            'created',
            'last_updated',
            'actions',
            'rendered_output',
        )
        default_columns = ('pk', 'assigned_object', 'zabbixhostgroup', 'rendered_output', 'inherited_from')


class ZabbixHostgroupAssignmentObjectViewTable(ZabbixInheritedAssignmentTable, NetBoxTable):
    name = tables.Column(linkify=True)
    assigned_object = tables.Column(verbose_name=_('Assigned To'), linkify=True, orderable=False)
    zabbixhostgroup = tables.Column(accessor='zabbixhostgroup.name', verbose_name=_('Zabbix Hostgroup'), linkify={'viewname': 'plugins:nbxsync:zabbixhostgroup', 'args': [A('zabbixhostgroup.pk')]})
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))
    actions = InheritanceAwareActionsColumn()

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
            'zabbixhostgroup',
            'inherited_from',
            'created',
            'last_updated',
            'actions',
            'rendered_output',
        )
        default_columns = ('pk', 'zabbixhostgroup', 'rendered_output', 'inherited_from')
