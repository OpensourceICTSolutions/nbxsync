from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixMaintenanceTagAssignmentFilterSet
from nbxsync.forms import ZabbixMaintenanceTagAssignmentBulkEditForm, ZabbixMaintenanceTagAssignmentFilterForm, ZabbixMaintenanceTagAssignmentForm
from nbxsync.models import ZabbixMaintenanceTagAssignment
from nbxsync.tables import ZabbixMaintenanceTagAssignmentTable

__all__ = (
    'ZabbixMaintenanceTagAssignmentListView',
    'ZabbixMaintenanceTagAssignmentView',
    'ZabbixMaintenanceTagAssignmentEditView',
    'ZabbixMaintenanceTagAssignmentBulkEditView',
    'ZabbixMaintenanceTagAssignmentDeleteView',
    'ZabbixMaintenanceTagAssignmentBulkDeleteView',
)


# ZabbixMaintenanceTagAssignment
@register_model_view(ZabbixMaintenanceTagAssignment, name='list')
class ZabbixMaintenanceTagAssignmentListView(ObjectListView):
    """
    List view of all ZabbixMaintenanceTagAssignment objects
    """

    queryset = ZabbixMaintenanceTagAssignment.objects.all()
    table = ZabbixMaintenanceTagAssignmentTable
    filterset = ZabbixMaintenanceTagAssignmentFilterSet
    filterset_form = ZabbixMaintenanceTagAssignmentFilterForm


@register_model_view(ZabbixMaintenanceTagAssignment)
class ZabbixMaintenanceTagAssignmentView(ObjectView):
    """
    ZabbixMaintenanceTagAssignment object view
    """

    queryset = ZabbixMaintenanceTagAssignment.objects.all()


@register_model_view(ZabbixMaintenanceTagAssignment, 'edit')
class ZabbixMaintenanceTagAssignmentEditView(ObjectEditView):
    """
    ZabbixMaintenanceTagAssignment Object Edit view
    """

    queryset = ZabbixMaintenanceTagAssignment.objects.all()
    form = ZabbixMaintenanceTagAssignmentForm


@register_model_view(ZabbixMaintenanceTagAssignment, 'bulk_edit')
class ZabbixMaintenanceTagAssignmentBulkEditView(BulkEditView):
    """
    ZabbixMaintenanceTagAssignment Object Bulk Edit view
    """

    queryset = ZabbixMaintenanceTagAssignment.objects.all()
    filterset = ZabbixMaintenanceTagAssignmentFilterSet
    table = ZabbixMaintenanceTagAssignmentTable
    form = ZabbixMaintenanceTagAssignmentBulkEditForm


@register_model_view(ZabbixMaintenanceTagAssignment, 'delete')
class ZabbixMaintenanceTagAssignmentDeleteView(ObjectDeleteView):
    queryset = ZabbixMaintenanceTagAssignment.objects.all()


@register_model_view(ZabbixMaintenanceTagAssignment, 'bulk_delete')
class ZabbixMaintenanceTagAssignmentBulkDeleteView(BulkDeleteView):
    """
    ZabbixMaintenanceTagAssignment Object Bulk Delete view
    """

    queryset = ZabbixMaintenanceTagAssignment.objects.all()
    filterset = ZabbixMaintenanceTagAssignmentFilterSet
    table = ZabbixMaintenanceTagAssignmentTable
