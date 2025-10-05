from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixMaintenancePeriodFilterSet
from nbxsync.forms import ZabbixMaintenancePeriodBulkEditForm, ZabbixMaintenancePeriodFilterForm, ZabbixMaintenancePeriodForm
from nbxsync.models import ZabbixMaintenancePeriod
from nbxsync.tables import ZabbixMaintenancePeriodTable

__all__ = (
    'ZabbixMaintenancePeriodListView',
    'ZabbixMaintenancePeriodView',
    'ZabbixMaintenancePeriodEditView',
    'ZabbixMaintenancePeriodBulkEditView',
    'ZabbixMaintenancePeriodDeleteView',
    'ZabbixMaintenancePeriodBulkDeleteView',
)


# ZabbixMaintenancePeriod
@register_model_view(ZabbixMaintenancePeriod, name='list')
class ZabbixMaintenancePeriodListView(ObjectListView):
    """
    List view of all ZabbixMaintenancePeriod objects
    """

    queryset = ZabbixMaintenancePeriod.objects.all()
    table = ZabbixMaintenancePeriodTable
    filterset = ZabbixMaintenancePeriodFilterSet
    filterset_form = ZabbixMaintenancePeriodFilterForm


@register_model_view(ZabbixMaintenancePeriod)
class ZabbixMaintenancePeriodView(ObjectView):
    """
    ZabbixMaintenancePeriod object view
    """

    queryset = ZabbixMaintenancePeriod.objects.all()


@register_model_view(ZabbixMaintenancePeriod, 'edit')
class ZabbixMaintenancePeriodEditView(ObjectEditView):
    """
    ZabbixMaintenancePeriod Object Edit view
    """

    queryset = ZabbixMaintenancePeriod.objects.all()
    form = ZabbixMaintenancePeriodForm
    template_name = 'nbxsync/forms/zabbixmaintenanceperiod.html'


@register_model_view(ZabbixMaintenancePeriod, 'bulk_edit')
class ZabbixMaintenancePeriodBulkEditView(BulkEditView):
    """
    ZabbixMaintenancePeriod Object Bulk Edit view
    """

    queryset = ZabbixMaintenancePeriod.objects.all()
    filterset = ZabbixMaintenancePeriodFilterSet
    table = ZabbixMaintenancePeriodTable
    form = ZabbixMaintenancePeriodBulkEditForm


@register_model_view(ZabbixMaintenancePeriod, 'delete')
class ZabbixMaintenancePeriodDeleteView(ObjectDeleteView):
    queryset = ZabbixMaintenancePeriod.objects.all()


@register_model_view(ZabbixMaintenancePeriod, 'bulk_delete')
class ZabbixMaintenancePeriodBulkDeleteView(BulkDeleteView):
    """
    ZabbixMaintenancePeriod Object Bulk Delete view
    """

    queryset = ZabbixMaintenancePeriod.objects.all()
    filterset = ZabbixMaintenancePeriodFilterSet
    table = ZabbixMaintenancePeriodTable
