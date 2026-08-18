from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

import django_tables2 as tables
from django_tables2.utils import A
from netbox.tables import NetBoxTable

from nbxsync.constants import ADD_HOSTINTERFACE_BUTTON
from nbxsync.models import ZabbixServerAssignment
from nbxsync.tables.columns import ContentTypeModelNameColumn, InheritanceAwareActionsColumn

__all__ = ('ZabbixServerAssignmentTable', 'ZabbixServerAssignmentObjectViewTable')


class InheritedSyncStatusColumn(tables.Column):
    """Renders sync status, showing neutral indicator for inherited assignments."""

    def render(self, record):
        # Inherited assignments are read-only copies — their sync status is
        # not persisted (by design). Show a neutral indicator instead of
        # misleading red X for "Never synced".
        if getattr(record, '_inherited_from', None):
            return format_html(
                '<i class="mdi mdi-sync text-muted" title="Inherited assignment ({}). ' 'Sync this host using the Zabbix sync action."></i>',
                record._inherited_from,
            )

        if record.last_sync_state:
            return format_html(
                '<i class="mdi mdi-check-bold text-success" title="{}: {}"></i>',
                record.last_sync.strftime('%d-%m-%Y %H:%M') if record.last_sync else '',
                record.last_sync_message,
            )
        if record.last_sync:
            return format_html(
                '<i class="mdi mdi-close-thick text-danger" title="{}: {}"></i>',
                record.last_sync.strftime('%d-%m-%Y %H:%M'),
                record.last_sync_message,
            )
        return format_html(
            '<i class="mdi mdi-close-thick text-danger" title="{}"></i>',
            record.last_sync_message,
        )


class ZabbixServerAssignmentTable(NetBoxTable):
    assigned_object = tables.Column(verbose_name=_('Assigned to'), linkify=True, orderable=False)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))
    zabbixserver = tables.Column(accessor='zabbixserver.name', verbose_name=_('Zabbix Server'), linkify={'viewname': 'plugins:nbxsync:zabbixserver', 'args': [A('zabbixserver.pk')]})
    zabbixproxy = tables.Column(accessor='zabbixproxy.name', verbose_name=_('Zabbix Proxy'), linkify={'viewname': 'plugins:nbxsync:zabbixproxy', 'args': [A('zabbixproxy.pk')]})
    zabbixproxygroup = tables.Column(accessor='zabbixproxygroup.name', verbose_name=_('Zabbix Proxygroup'), linkify={'viewname': 'plugins:nbxsync:zabbixproxygroup', 'args': [A('zabbixproxygroup.pk')]})
    actions = InheritanceAwareActionsColumn()

    class Meta(NetBoxTable.Meta):
        model = ZabbixServerAssignment
        fields = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'zabbixserver',
            'zabbixproxy',
            'zabbixproxygroup',
            'sync_status',
            'sync_enabled',
            'created',
            'last_updated',
            'actions',
        )
        default_columns = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'zabbixserver',
            'zabbixproxy',
            'zabbixproxygroup',
            'sync_status',
            'sync_enabled',
            'actions',
        )


class ZabbixServerAssignmentObjectViewTable(NetBoxTable):
    assigned_object = tables.Column(verbose_name=_('Assigned To'), linkify=True, orderable=False)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))
    zabbixserver = tables.Column(accessor='zabbixserver.name', verbose_name=_('Zabbix Server'), linkify={'viewname': 'plugins:nbxsync:zabbixserver', 'args': [A('zabbixserver.pk')]})
    zabbixproxy = tables.Column(accessor='zabbixproxy.name', verbose_name=_('Zabbix Proxy'), linkify={'viewname': 'plugins:nbxsync:zabbixproxy', 'args': [A('zabbixproxy.pk')]})
    zabbixproxygroup = tables.Column(accessor='zabbixproxygroup.name', verbose_name=_('Zabbix Proxygroup'), linkify={'viewname': 'plugins:nbxsync:zabbixproxygroup', 'args': [A('zabbixproxygroup.pk')]})
    sync_status = InheritedSyncStatusColumn(accessor=tables.A('pk'), verbose_name=_('Sync status'), orderable=False)
    sync_enabled = tables.TemplateColumn(
        template_code="""
            {% if record.sync_enabled %}
                {% if record.zabbixserver.sync_enabled %}
                    <i class="mdi mdi-check-bold text-success" title="Enabled"></i>
                {% else %}
                    <i class="mdi mdi-close-thick text-danger" title="Server sync disabled"></i>
                {% endif %}
            {% else %}
                <i class="mdi mdi-close-thick text-danger" title="Disabled"></i>
            {% endif %}
        """,
        orderable=False,
    )
    actions = InheritanceAwareActionsColumn(extra_buttons=ADD_HOSTINTERFACE_BUTTON)

    class Meta(NetBoxTable.Meta):
        model = ZabbixServerAssignment
        fields = (
            'pk',
            'assigned_object_type',
            'assigned_object',
            'zabbixserver',
            'zabbixproxy',
            'zabbixproxygroup',
            'sync_status',
            'sync_enabled',
            'created',
            'last_updated',
            'actions',
        )
        default_columns = (
            'pk',
            'zabbixserver',
            'zabbixproxy',
            'zabbixproxygroup',
            'sync_status',
            'sync_enabled',
        )
