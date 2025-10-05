import django_tables2 as tables
from django.utils.translation import gettext_lazy as _
from django_tables2.utils import A

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixTagAssignment
from nbxsync.tables import ZabbixInheritedAssignmentTable
from nbxsync.tables.columns import ContentTypeModelNameColumn, InheritanceAwareActionsColumn

__all__ = ('ZabbixTagAssignmentTable', 'ZabbixTagAssignmentObjectViewTable')


class ZabbixTagAssignmentTable(ZabbixInheritedAssignmentTable, NetBoxTable):
    name = tables.Column(linkify=True)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))
    assigned_object = tables.Column(verbose_name=_('Assigned To'), linkify=True, orderable=False)
    zabbixtag = tables.Column(accessor='zabbixtag.name', verbose_name=_('Zabbix Tag'), linkify={'viewname': 'plugins:nbxsync:zabbixtag', 'args': [A('zabbixtag.pk')]})
    actions = InheritanceAwareActionsColumn()

    rendered_output = tables.TemplateColumn(
        template_code="""
        {% load zabbix_tags %}
        {% render_zabbix_tag_assignment record as rendered_output %}
        {{ rendered_output|escape }}
        """,
        verbose_name='Value',
    )

    class Meta(NetBoxTable.Meta):
        model = ZabbixTagAssignment
        fields = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'zabbixtag',
            'inherited_from',
            'created',
            'last_updated',
            'actions',
            'rendered_output',
        )
        default_columns = ('pk', 'assigned_object', 'zabbixtag', 'rendered_output', 'inherited_from')


class ZabbixTagAssignmentObjectViewTable(ZabbixInheritedAssignmentTable, NetBoxTable):
    name = tables.Column(linkify=True)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))
    assigned_object = tables.Column(verbose_name=_('Assigned To'), linkify=True, orderable=False)
    zabbixtag = tables.Column(accessor='zabbixtag.name', verbose_name=_('Zabbix Tag'), linkify={'viewname': 'plugins:nbxsync:zabbixtag', 'args': [A('zabbixtag.pk')]})
    actions = InheritanceAwareActionsColumn()

    rendered_output = tables.TemplateColumn(
        template_code="""
        {% load zabbix_tags %}
        {% render_zabbix_tag_assignment record as rendered_output %}
        {{ rendered_output|escape }}
        """,
        verbose_name='Value',
    )

    class Meta(NetBoxTable.Meta):
        model = ZabbixTagAssignment
        fields = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'zabbixtag',
            'inherited_from',
            'created',
            'last_updated',
            'actions',
            'rendered_output',
        )
        default_columns = ('pk', 'zabbixtag', 'rendered_output', 'inherited_from')
