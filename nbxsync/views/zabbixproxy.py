from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.choices import ZabbixProxyTypeChoices, ZabbixTLSChoices
from nbxsync.filtersets import ZabbixProxyFilterSet
from nbxsync.forms import ZabbixProxyBulkEditForm, ZabbixProxyFilterForm, ZabbixProxyForm
from nbxsync.models import ZabbixProxy
from nbxsync.tables import ZabbixProxyTable

__all__ = ('ZabbixProxyListView', 'ZabbixProxyView', 'ZabbixProxyEditView', 'ZabbixProxyBulkEditView', 'ZabbixProxyDeleteView', 'ZabbixProxyBulkDeleteView')


# ZabbixProxy
@register_model_view(ZabbixProxy, name='list')
class ZabbixProxyListView(ObjectListView):
    """
    List view of all ZabbixProxy objects
    """

    queryset = ZabbixProxy.objects.all()
    table = ZabbixProxyTable
    filterset = ZabbixProxyFilterSet
    filterset_form = ZabbixProxyFilterForm


@register_model_view(ZabbixProxy)
class ZabbixProxyView(ObjectView):
    """
    ZabbixProxy object view
    """

    queryset = ZabbixProxy.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        context['ZabbixProxyTypeChoices'] = ZabbixProxyTypeChoices
        context['ZabbixTLSChoices'] = ZabbixTLSChoices
        return context


@register_model_view(ZabbixProxy, 'edit')
class ZabbixProxyEditView(ObjectEditView):
    """
    ZabbixProxy Object Edit view
    """

    queryset = ZabbixProxy.objects.all()
    form = ZabbixProxyForm
    template_name = 'nbxsync/forms/zabbixproxy.html'


@register_model_view(ZabbixProxy, 'bulk_edit')
class ZabbixProxyBulkEditView(BulkEditView):
    """
    ZabbixProxy Object Bulk Edit view
    """

    queryset = ZabbixProxy.objects.all()
    filterset = ZabbixProxyFilterSet
    table = ZabbixProxyTable
    form = ZabbixProxyBulkEditForm


@register_model_view(ZabbixProxy, 'delete')
class ZabbixProxyDeleteView(ObjectDeleteView):
    queryset = ZabbixProxy.objects.all()


@register_model_view(ZabbixProxy, 'bulk_delete')
class ZabbixProxyBulkDeleteView(BulkDeleteView):
    """
    ZabbixProxy Object Bulk Delete view
    """

    queryset = ZabbixProxy.objects.all()
    filterset = ZabbixProxyFilterSet
    table = ZabbixProxyTable
