from netbox.views.generic import BulkDeleteView, BulkImportView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixServerFilterSet
from nbxsync.forms import ZabbixServerBulkEditForm, ZabbixServerFilterForm, ZabbixServerForm, ZabbixServerBulkImportForm
from nbxsync.models import ZabbixServer, ZabbixTemplate
from nbxsync.tables import ZabbixServerTable

__all__ = ('ZabbixServerListView', 'ZabbixServerView', 'ZabbixServerEditView', 'ZabbixServerBulkImportView', 'ZabbixServerBulkEditView', 'ZabbixServerDeleteView', 'ZabbixServerBulkDeleteView')


# ZabbixServer
@register_model_view(ZabbixServer, name='list')
class ZabbixServerListView(ObjectListView):
    """
    List view of all ZabbixServer objects
    """

    queryset = ZabbixServer.objects.all()
    table = ZabbixServerTable
    filterset = ZabbixServerFilterSet
    filterset_form = ZabbixServerFilterForm


@register_model_view(ZabbixServer)
class ZabbixServerView(ObjectView):
    """
    ZabbixServer object view
    """

    queryset = ZabbixServer.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        # Get all Templates linked to this ZabbixServer
        template_count = ZabbixTemplate.objects.filter(zabbixserver=instance).count()

        context['template_count'] = template_count

        return context


@register_model_view(ZabbixServer, 'edit')
class ZabbixServerEditView(ObjectEditView):
    """
    ZabbixServer Object Edit view
    """

    queryset = ZabbixServer.objects.all()
    form = ZabbixServerForm
    template_name = 'nbxsync/zabbixserver_edit.html'


@register_model_view(ZabbixServer, 'bulk_import')
class ZabbixServerBulkImportView(BulkImportView):
    queryset = ZabbixServer.objects.all()
    model_form = ZabbixServerBulkImportForm
    table = ZabbixServerTable


@register_model_view(ZabbixServer, 'bulk_edit')
class ZabbixServerBulkEditView(BulkEditView):
    """
    ZabbixServer Object Bulk Edit view
    """

    queryset = ZabbixServer.objects.all()
    filterset = ZabbixServerFilterSet
    table = ZabbixServerTable
    form = ZabbixServerBulkEditForm


@register_model_view(ZabbixServer, 'delete')
class ZabbixServerDeleteView(ObjectDeleteView):
    queryset = ZabbixServer.objects.all()


@register_model_view(ZabbixServer, 'bulk_delete')
class ZabbixServerBulkDeleteView(BulkDeleteView):
    """
    ZabbixServer Object Bulk Delete view
    """

    queryset = ZabbixServer.objects.all()
    filterset = ZabbixServerFilterSet
    table = ZabbixServerTable
