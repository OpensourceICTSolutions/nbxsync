import django_tables2 as tables
from django.utils.translation import gettext_lazy as _
from django_tables2.utils import A

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixTemplateAssignment
from nbxsync.tables import ZabbixInheritedAssignmentTable
from nbxsync.tables.columns import ContentTypeModelNameColumn, InheritanceAwareActionsColumn

__all__ = ('ZabbixTemplateAssignmentTable', 'ZabbixTemplateAssignmentObjectViewTable')


class ZabbixTemplateAssignmentTable(ZabbixInheritedAssignmentTable, NetBoxTable):
    name = tables.Column(linkify=True)
    assigned_object = tables.Column(verbose_name=_('Assigned To'), linkify=True, orderable=False)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))
    zabbixtemplate = tables.Column(accessor='zabbixtemplate.name', verbose_name=_('Zabbix Template'), linkify={'viewname': 'plugins:nbxsync:zabbixtemplate', 'args': [A('zabbixtemplate.pk')]})
    actions = InheritanceAwareActionsColumn()

    class Meta(NetBoxTable.Meta):
        model = ZabbixTemplateAssignment
        fields = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'zabbixtemplate',
            'inherited_from',
            'created',
            'last_updated',
            'actions',
        )
        default_columns = ('pk', 'assigned_object', 'zabbixtemplate', 'inherited_from')


class ZabbixTemplateAssignmentObjectViewTable(ZabbixInheritedAssignmentTable, NetBoxTable):
    name = tables.Column(linkify=True)
    assigned_object = tables.Column(verbose_name=_('Assigned To'), linkify=True, orderable=False)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))

    zabbixtemplate = tables.Column(accessor='zabbixtemplate.name', verbose_name='Zabbix Template', linkify={'viewname': 'plugins:nbxsync:zabbixtemplate', 'args': [A('zabbixtemplate.pk')]})
    actions = InheritanceAwareActionsColumn()

    class Meta(NetBoxTable.Meta):
        model = ZabbixTemplateAssignment
        fields = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'zabbixtemplate',
            'inherited_from',
            'created',
            'last_updated',
            'actions',
        )
        default_columns = ('pk', 'zabbixtemplate', 'inherited_from')
