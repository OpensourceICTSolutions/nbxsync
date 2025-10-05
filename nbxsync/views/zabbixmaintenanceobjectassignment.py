from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixMaintenanceObjectAssignmentFilterSet
from nbxsync.forms import ZabbixMaintenanceObjectAssignmentBulkEditForm, ZabbixMaintenanceObjectAssignmentFilterForm, ZabbixMaintenanceObjectAssignmentForm
from nbxsync.models import ZabbixMaintenanceObjectAssignment
from nbxsync.tables import ZabbixMaintenanceObjectAssignmentTable

__all__ = (
    'ZabbixMaintenanceObjectAssignmentListView',
    'ZabbixMaintenanceObjectAssignmentView',
    'ZabbixMaintenanceObjectAssignmentEditView',
    'ZabbixMaintenanceObjectAssignmentBulkEditView',
    'ZabbixMaintenanceObjectAssignmentDeleteView',
    'ZabbixMaintenanceObjectAssignmentBulkDeleteView',
)


# ZabbixMaintenanceObjectAssignment
@register_model_view(ZabbixMaintenanceObjectAssignment, name='list')
class ZabbixMaintenanceObjectAssignmentListView(ObjectListView):
    """
    List view of all ZabbixMaintenanceObjectAssignment objects
    """

    queryset = ZabbixMaintenanceObjectAssignment.objects.all()
    table = ZabbixMaintenanceObjectAssignmentTable
    filterset = ZabbixMaintenanceObjectAssignmentFilterSet
    filterset_form = ZabbixMaintenanceObjectAssignmentFilterForm


@register_model_view(ZabbixMaintenanceObjectAssignment)
class ZabbixMaintenanceObjectAssignmentView(ObjectView):
    """
    ZabbixMaintenanceObjectAssignment object view
    """

    queryset = ZabbixMaintenanceObjectAssignment.objects.all()


@register_model_view(ZabbixMaintenanceObjectAssignment, 'edit')
class ZabbixMaintenanceObjectAssignmentEditView(ObjectEditView):
    """
    ZabbixMaintenanceObjectAssignment Object Edit view
    """

    queryset = ZabbixMaintenanceObjectAssignment.objects.all()
    form = ZabbixMaintenanceObjectAssignmentForm


@register_model_view(ZabbixMaintenanceObjectAssignment, 'bulk_edit')
class ZabbixMaintenanceObjectAssignmentBulkEditView(BulkEditView):
    """
    ZabbixMaintenanceObjectAssignment Object Bulk Edit view
    """

    queryset = ZabbixMaintenanceObjectAssignment.objects.all()
    filterset = ZabbixMaintenanceObjectAssignmentFilterSet
    table = ZabbixMaintenanceObjectAssignmentTable
    form = ZabbixMaintenanceObjectAssignmentBulkEditForm


@register_model_view(ZabbixMaintenanceObjectAssignment, 'delete')
class ZabbixMaintenanceObjectAssignmentDeleteView(ObjectDeleteView):
    queryset = ZabbixMaintenanceObjectAssignment.objects.all()


@register_model_view(ZabbixMaintenanceObjectAssignment, 'bulk_delete')
class ZabbixMaintenanceObjectAssignmentBulkDeleteView(BulkDeleteView):
    """
    ZabbixMaintenanceObjectAssignment Object Bulk Delete view
    """

    queryset = ZabbixMaintenanceObjectAssignment.objects.all()
    filterset = ZabbixMaintenanceObjectAssignmentFilterSet
    table = ZabbixMaintenanceObjectAssignmentTable
