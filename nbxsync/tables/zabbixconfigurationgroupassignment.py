import django_tables2 as tables
from django.utils.translation import gettext_lazy as _
from django_tables2.utils import A

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixConfigurationGroupAssignment
from nbxsync.tables.columns import ContentTypeModelNameColumn

__all__ = ('ZabbixConfigurationGroupAssignmentTable', 'ZabbixConfigurationGroupAssignmentObjectViewTable', 'ZabbixConfigurationGroupAssignmentDetailViewTable')


class ZabbixConfigurationGroupAssignmentTable(NetBoxTable):
    zabbixconfigurationgroup = tables.Column(accessor='zabbixconfigurationgroup.name', verbose_name=_('Zabbix Configuration Group'), linkify={'viewname': 'plugins:nbxsync:zabbixconfigurationgroup', 'args': [A('zabbixconfigurationgroup.pk')]})
    assigned_object = tables.Column(verbose_name=_('Object'), linkify=True, orderable=False)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))

    class Meta(NetBoxTable.Meta):
        model = ZabbixConfigurationGroupAssignment
        fields = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'zabbixconfigurationgroup',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'zabbixconfigurationgroup',
            'assigned_object',
        )


class ZabbixConfigurationGroupAssignmentObjectViewTable(NetBoxTable):
    assigned_object = tables.Column(verbose_name=_('Object'), linkify=True, orderable=False)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))

    class Meta(NetBoxTable.Meta):
        model = ZabbixConfigurationGroupAssignment
        fields = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'assigned_object_type',
            'assigned_object',
        )


class ZabbixConfigurationGroupAssignmentDetailViewTable(NetBoxTable):
    zabbixconfigurationgroup = tables.Column(accessor='zabbixconfigurationgroup.name', verbose_name=_('Zabbix Configuration Group'), linkify={'viewname': 'plugins:nbxsync:zabbixconfigurationgroup', 'args': [A('zabbixconfigurationgroup.pk')]})
    assigned_object = tables.Column(verbose_name=_('Object'), linkify=True, orderable=False)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))

    class Meta(NetBoxTable.Meta):
        model = ZabbixConfigurationGroupAssignment
        fields = (
            'pk',
            'zabbixconfigurationgroup',
            'assigned_object_type',
            'assigned_object',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'assigned_object_type',
            'assigned_object',
        )
