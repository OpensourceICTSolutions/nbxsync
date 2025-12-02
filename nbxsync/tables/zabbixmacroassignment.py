import django_tables2 as tables
from django.utils.translation import gettext_lazy as _
from django_tables2.utils import A

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixMacroAssignment
from nbxsync.tables import ZabbixInheritedAssignmentTable
from nbxsync.tables.columns import ContentTypeModelNameColumn, InheritanceAwareActionsColumn
from nbxsync.choices import ZabbixMacroTypeChoices

__all__ = ('ZabbixMacroAssignmentTable', 'ZabbixMacroAssignmentObjectViewTable')


class ZabbixMacroAssignmentTable(ZabbixInheritedAssignmentTable, NetBoxTable):
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))
    assigned_object = tables.Column(verbose_name=_('Assigned To'), linkify=True, orderable=False)
    zabbixmacro = tables.Column(accessor='zabbixmacro.macro', verbose_name=_('Zabbix Macro'), linkify={'viewname': 'plugins:nbxsync:zabbixmacro', 'args': [A('zabbixmacro.pk')]})
    macro_full_name = tables.Column(accessor='full_name', verbose_name=_('Macro'), order_by='zabbixmacro__macro')
    actions = InheritanceAwareActionsColumn()

    class Meta(NetBoxTable.Meta):
        model = ZabbixMacroAssignment
        fields = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'zabbixmacro',
            'macro_full_name',
            'inherited_from',
            'is_context',
            'regex',
            'value',
            'created',
            'last_updated',
            'actions,',
        )
        default_columns = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'zabbixmacro',
            'macro_full_name',
            'is_context',
            'regex',
            'value',
            'inherited_from',
        )

    def render_value(self, value, record):
        if getattr(record.zabbixmacro, 'type', None) == ZabbixMacroTypeChoices.SECRET:
            return '****'
        return value


class ZabbixMacroAssignmentObjectViewTable(ZabbixInheritedAssignmentTable, NetBoxTable):
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))
    assigned_object = tables.Column(verbose_name=_('Assigned To'), linkify=True, orderable=False)
    macro_full_name = tables.Column(accessor='full_name', verbose_name=_('Macro'), order_by='zabbixmacro__macro', linkify={'viewname': 'plugins:nbxsync:zabbixmacro', 'args': [A('zabbixmacro.pk')]})
    actions = InheritanceAwareActionsColumn()
    value = tables.Column(verbose_name='Value')

    class Meta(NetBoxTable.Meta):
        model = ZabbixMacroAssignment
        fields = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'zabbixmacro',
            'macro_full_name',
            'inherited_from',
            'is_regex',
            'context',
            'value',
            'created',
            'last_updated',
            'actions,',
        )
        default_columns = (
            'pk',
            'macro_full_name',
            'is_regex',
            'context',
            'value',
            'inherited_from',
        )

    def render_value(self, value, record):
        if getattr(record.zabbixmacro, 'type', None) == ZabbixMacroTypeChoices.SECRET:
            return '****'
        return value
