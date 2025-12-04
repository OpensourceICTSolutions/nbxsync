import django_tables2 as tables
from django_tables2.utils import A
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixServerAssignment
from nbxsync.tables.columns import ContentTypeModelNameColumn, InheritanceAwareActionsColumn
from nbxsync.constants import ADD_HOSTINTERFACE_BUTTON

__all__ = ('ZabbixServerAssignmentTable', 'ZabbixServerAssignmentObjectViewTable')


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
        )


class ZabbixServerAssignmentObjectViewTable(NetBoxTable):
    assigned_object = tables.Column(verbose_name=_('Assigned To'), linkify=True, orderable=False)
    assigned_object_type = ContentTypeModelNameColumn(accessor='assigned_object_type', verbose_name=_('Object Type'), order_by=('assigned_object_type__model',))
    zabbixserver = tables.Column(accessor='zabbixserver.name', verbose_name=_('Zabbix Server'), linkify={'viewname': 'plugins:nbxsync:zabbixserver', 'args': [A('zabbixserver.pk')]})
    zabbixproxy = tables.Column(accessor='zabbixproxy.name', verbose_name=_('Zabbix Proxy'), linkify={'viewname': 'plugins:nbxsync:zabbixproxy', 'args': [A('zabbixproxy.pk')]})
    zabbixproxygroup = tables.Column(accessor='zabbixproxygroup.name', verbose_name=_('Zabbix Proxygroup'), linkify={'viewname': 'plugins:nbxsync:zabbixproxygroup', 'args': [A('zabbixproxygroup.pk')]})
    sync_status = tables.TemplateColumn(
        template_code="""
            {% if record.last_sync_state %}
                <i class="mdi mdi-check-bold text-success" title="{{ record.last_sync|date:'d-m-Y H:i' }}: {{ record.last_sync_message }}"></i>
            {% else %}
                <i class="mdi mdi-close-thick text-danger" title="{{ record.last_sync|date:'d-m-Y H:i' }}: {{ record.last_sync_message }}"></i>
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
        )
