import django_tables2 as tables
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_tables2.utils import A

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixMaintenanceObjectAssignment
from nbxsync.tables.columns import ContentTypeModelNameColumn

__all__ = ('ZabbixMaintenanceObjectAssignmentTable', 'ZabbixMaintenanceObjectAssignmentObjectViewTable', 'ZabbixMaintenanceObjectAssignmentDetailViewTable')


class ZabbixMaintenanceObjectAssignmentTable(NetBoxTable):
    zabbixmaintenance = tables.Column(accessor='zabbixmaintenance.name', verbose_name=_('Zabbix Maintenance'), linkify={'viewname': 'plugins:nbxsync:zabbixmaintenance', 'args': [A('zabbixmaintenance.pk')]})
    assigned_object = tables.Column(verbose_name=_('Object'), linkify=True, orderable=False)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))

    class Meta(NetBoxTable.Meta):
        model = ZabbixMaintenanceObjectAssignment
        fields = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'zabbixmaintenance',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'zabbixmaintenance',
            'assigned_object',
        )


class ZabbixMaintenanceObjectAssignmentObjectViewTable(NetBoxTable):
    assigned_object = tables.Column(verbose_name=_('Object'), linkify=True, orderable=False)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))

    class Meta(NetBoxTable.Meta):
        model = ZabbixMaintenanceObjectAssignment
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


class ZabbixMaintenanceObjectAssignmentDetailViewTable(NetBoxTable):
    zabbixmaintenance = tables.Column(accessor='zabbixmaintenance.name', verbose_name=_('Zabbix Maintenance'), linkify={'viewname': 'plugins:nbxsync:zabbixmaintenance', 'args': [A('zabbixmaintenance.pk')]})
    zabbixmaintenance_active_since = tables.DateTimeColumn(accessor='zabbixmaintenance.active_since', verbose_name=_('Active Since'), format='d-m-Y H:i', linkify={'viewname': 'plugins:nbxsync:zabbixmaintenance', 'args': [A('zabbixmaintenance.pk')]})
    zabbixmaintenance_active_till = tables.DateTimeColumn(accessor='zabbixmaintenance.active_till', verbose_name=_('Active Till'), format='d-m-Y H:i', linkify={'viewname': 'plugins:nbxsync:zabbixmaintenance', 'args': [A('zabbixmaintenance.pk')]})
    active = tables.Column(empty_values=(), verbose_name=_('Active'))

    class Meta(NetBoxTable.Meta):
        model = ZabbixMaintenanceObjectAssignment
        fields = (
            'pk',
            'zabbixmaintenance',
            'zabbixmaintenance_active_since',
            'zabbixmaintenance_active_till',
            'active',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'zabbixmaintenance',
            'zabbixmaintenance_active_since',
            'zabbixmaintenance_active_till',
            'active',
        )

    def render_active(self, record):
        active_till = record.zabbixmaintenance.active_till
        now = timezone.now()
        if active_till and now > active_till:
            return mark_safe('<i class="mdi mdi-close-thick text-danger"></i>')
        return mark_safe('<i class="mdi mdi-check-bold text-success"></i>')
