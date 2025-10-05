from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixHostInventoryFilterSet
from nbxsync.forms import ZabbixHostInventoryBulkEditForm, ZabbixHostInventoryFilterForm, ZabbixHostInventoryForm
from nbxsync.models import ZabbixHostInventory
from nbxsync.tables import ZabbixHostInventoryTable

__all__ = (
    'ZabbixHostInventoryListView',
    'ZabbixHostInventoryView',
    'ZabbixHostInventoryEditView',
    'ZabbixHostInventoryBulkEditView',
    'ZabbixHostInventoryDeleteView',
    'ZabbixHostInventoryBulkDeleteView',
)


# ZabbixHostInventory
@register_model_view(ZabbixHostInventory, name='list')
class ZabbixHostInventoryListView(ObjectListView):
    """
    List view of all ZabbixHostInventory objects
    """

    queryset = ZabbixHostInventory.objects.all()
    table = ZabbixHostInventoryTable
    filterset = ZabbixHostInventoryFilterSet
    filterset_form = ZabbixHostInventoryFilterForm


@register_model_view(ZabbixHostInventory)
class ZabbixHostInventoryView(ObjectView):
    """
    ZabbixHostInventory object view
    """

    queryset = ZabbixHostInventory.objects.all()


@register_model_view(ZabbixHostInventory, 'edit')
class ZabbixHostInventoryEditView(ObjectEditView):
    """
    ZabbixHostInventory Object Edit view
    """

    queryset = ZabbixHostInventory.objects.all()
    form = ZabbixHostInventoryForm


@register_model_view(ZabbixHostInventory, 'bulk_edit')
class ZabbixHostInventoryBulkEditView(BulkEditView):
    """
    ZabbixHostInventory Object Bulk Edit view
    """

    queryset = ZabbixHostInventory.objects.all()
    filterset = ZabbixHostInventoryFilterSet
    table = ZabbixHostInventoryTable
    form = ZabbixHostInventoryBulkEditForm


@register_model_view(ZabbixHostInventory, 'delete')
class ZabbixHostInventoryDeleteView(ObjectDeleteView):
    queryset = ZabbixHostInventory.objects.all()


@register_model_view(ZabbixHostInventory, 'bulk_delete')
class ZabbixHostInventoryBulkDeleteView(BulkDeleteView):
    """
    ZabbixHostInventory Object Bulk Delete view
    """

    queryset = ZabbixHostInventory.objects.all()
    filterset = ZabbixHostInventoryFilterSet
    table = ZabbixHostInventoryTable
