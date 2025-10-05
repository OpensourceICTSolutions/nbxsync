from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixProxyGroupFilterSet
from nbxsync.forms import ZabbixProxyGroupBulkEditForm, ZabbixProxyGroupFilterForm, ZabbixProxyGroupForm
from nbxsync.models import ZabbixProxy, ZabbixProxyGroup
from nbxsync.tables import ZabbixProxyGroupTable, ZabbixProxyObjectViewTable

__all__ = (
    'ZabbixProxyGroupListView',
    'ZabbixProxyGroupView',
    'ZabbixProxyGroupEditView',
    'ZabbixProxyGroupBulkEditView',
    'ZabbixProxyGroupDeleteView',
    'ZabbixProxyGroupBulkDeleteView',
)


# ZabbixProxyGroup
@register_model_view(ZabbixProxyGroup, name='list')
class ZabbixProxyGroupListView(ObjectListView):
    """
    List view of all ZabbixProxyGroup objects
    """

    queryset = ZabbixProxyGroup.objects.all()
    table = ZabbixProxyGroupTable
    filterset = ZabbixProxyGroupFilterSet
    filterset_form = ZabbixProxyGroupFilterForm


@register_model_view(ZabbixProxyGroup)
class ZabbixProxyGroupView(ObjectView):
    """
    ZabbixProxyGroup object view
    """

    queryset = ZabbixProxyGroup.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        # Get all proxies assigned to this ProxyGroup is used
        proxies = ZabbixProxy.objects.filter(proxygroup=instance)

        if proxies:
            objectassignment_table = ZabbixProxyObjectViewTable(proxies)
            objectassignment_table.configure(request)
        else:
            objectassignment_table = None

        context['objectassignment_table'] = objectassignment_table

        return context


@register_model_view(ZabbixProxyGroup, 'edit')
class ZabbixProxyGroupEditView(ObjectEditView):
    """
    ZabbixProxyGroup Object Edit view
    """

    queryset = ZabbixProxyGroup.objects.all()
    form = ZabbixProxyGroupForm


@register_model_view(ZabbixProxyGroup, 'bulk_edit')
class ZabbixProxyGroupBulkEditView(BulkEditView):
    """
    ZabbixProxyGroup Object Bulk Edit view
    """

    queryset = ZabbixProxyGroup.objects.all()
    filterset = ZabbixProxyGroupFilterSet
    table = ZabbixProxyGroupTable
    form = ZabbixProxyGroupBulkEditForm


@register_model_view(ZabbixProxyGroup, 'delete')
class ZabbixProxyGroupDeleteView(ObjectDeleteView):
    queryset = ZabbixProxyGroup.objects.all()


@register_model_view(ZabbixProxyGroup, 'bulk_delete')
class ZabbixProxyGroupBulkDeleteView(BulkDeleteView):
    """
    ZabbixProxyGroup Object Bulk Delete view
    """

    queryset = ZabbixProxyGroup.objects.all()
    filterset = ZabbixProxyGroupFilterSet
    table = ZabbixProxyGroupTable
