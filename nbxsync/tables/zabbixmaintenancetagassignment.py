import django_tables2 as tables
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_tables2.utils import A

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixMaintenanceTagAssignment

__all__ = ('ZabbixMaintenanceTagAssignmentTable', 'ZabbixMaintenanceTagAssignmentObjectViewTable', 'ZabbixMaintenanceTagAssignmentDetailViewTable')


class ZabbixMaintenanceTagAssignmentTable(NetBoxTable):
    zabbixmaintenance = tables.Column(accessor='zabbixmaintenance.name', verbose_name=_('Zabbix Maintenance'), linkify={'viewname': 'plugins:nbxsync:zabbixmaintenance', 'args': [A('zabbixmaintenance.pk')]})
    zabbixtag = tables.Column(accessor='zabbixtag.name', verbose_name=_('Zabbix Tag'), linkify={'viewname': 'plugins:nbxsync:zabbixtag', 'args': [A('zabbixtag.pk')]})

    class Meta(NetBoxTable.Meta):
        model = ZabbixMaintenanceTagAssignment
        fields = (
            'pk',
            'zabbixmaintenance',
            'zabbixtag',
            'operator',
            'value',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'zabbixmaintenance',
            'zabbixtag',
            'operator',
            'value',
        )


class ZabbixMaintenanceTagAssignmentObjectViewTable(NetBoxTable):
    zabbixtag_name = tables.Column(accessor='zabbixtag.name', verbose_name=_('Zabbix Tag'), linkify={'viewname': 'plugins:nbxsync:zabbixtag', 'args': [A('zabbixtag.pk')]})
    zabbixtag_tag = tables.Column(accessor='zabbixtag.tag', verbose_name=_('Zabbix Tag'), linkify={'viewname': 'plugins:nbxsync:zabbixtag', 'args': [A('zabbixtag.pk')]})

    class Meta(NetBoxTable.Meta):
        model = ZabbixMaintenanceTagAssignment
        fields = (
            'pk',
            'zabbixtag_name',
            'zabbixtag_tag',
            'operator',
            'value',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'zabbixtag_name',
            'zabbixtag_tag',
            'operator',
            'value',
        )


class ZabbixMaintenanceTagAssignmentDetailViewTable(NetBoxTable):
    zabbixmaintenance = tables.Column(accessor='zabbixmaintenance.name', verbose_name=_('Zabbix Maintenance'), linkify={'viewname': 'plugins:nbxsync:zabbixmaintenance', 'args': [A('zabbixmaintenance.pk')]})
    zabbixmaintenance_active_since = tables.DateTimeColumn(accessor='zabbixmaintenance.active_since', verbose_name=_('Active Since'), format='d-m-Y H:i', linkify={'viewname': 'plugins:nbxsync:zabbixmaintenance', 'args': [A('zabbixmaintenance.pk')]})
    zabbixmaintenance_active_till = tables.DateTimeColumn(accessor='zabbixmaintenance.active_till', verbose_name=_('Active Till'), format='d-m-Y H:i', linkify={'viewname': 'plugins:nbxsync:zabbixmaintenance', 'args': [A('zabbixmaintenance.pk')]})
    active = tables.Column(empty_values=(), verbose_name=_('Active'))

    class Meta(NetBoxTable.Meta):
        model = ZabbixMaintenanceTagAssignment
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
