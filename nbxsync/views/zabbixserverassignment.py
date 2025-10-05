from netbox.views.generic import BulkDeleteView, BulkImportView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixServerAssignmentFilterSet
from nbxsync.forms import ZabbixServerAssignmentBulkImportForm, ZabbixServerAssignmentBulkEditForm, ZabbixServerAssignmentFilterForm, ZabbixServerAssignmentForm
from nbxsync.models import ZabbixServerAssignment
from nbxsync.tables import ZabbixServerAssignmentTable

__all__ = ('ZabbixServerAssignmentListView', 'ZabbixServerAssignmentView', 'ZabbixServerAssignmentEditView', 'ZabbixServerAssignmentBulkImportView', 'ZabbixServerAssignmentBulkEditView', 'ZabbixServerAssignmentDeleteView', 'ZabbixServerAssignmentBulkDeleteView')


# ZabbixServerAssignment
@register_model_view(ZabbixServerAssignment, name='list')
class ZabbixServerAssignmentListView(ObjectListView):
    """
    List view of all ZabbixServerAssignment objects
    """

    queryset = ZabbixServerAssignment.objects.all()
    table = ZabbixServerAssignmentTable
    filterset = ZabbixServerAssignmentFilterSet
    filterset_form = ZabbixServerAssignmentFilterForm


@register_model_view(ZabbixServerAssignment)
class ZabbixServerAssignmentView(ObjectView):
    """
    ZabbixServerAssignment object view
    """

    queryset = ZabbixServerAssignment.objects.all()


@register_model_view(ZabbixServerAssignment, 'edit')
class ZabbixServerAssignmentEditView(ObjectEditView):
    """
    ZabbixServerAssignment Object Edit view
    """

    queryset = ZabbixServerAssignment.objects.all()
    form = ZabbixServerAssignmentForm


@register_model_view(ZabbixServerAssignment, 'bulk_import')
class ZabbixServerAssignmentBulkImportView(BulkImportView):
    queryset = ZabbixServerAssignment.objects.all()
    model_form = ZabbixServerAssignmentBulkImportForm
    table = ZabbixServerAssignmentTable


@register_model_view(ZabbixServerAssignment, 'bulk_edit')
class ZabbixServerAssignmentBulkEditView(BulkEditView):
    """
    ZabbixServerAssignment Object Bulk Edit view
    """

    queryset = ZabbixServerAssignment.objects.all()
    filterset = ZabbixServerAssignmentFilterSet
    table = ZabbixServerAssignmentTable
    form = ZabbixServerAssignmentBulkEditForm


@register_model_view(ZabbixServerAssignment, 'delete')
class ZabbixServerAssignmentDeleteView(ObjectDeleteView):
    queryset = ZabbixServerAssignment.objects.all()


@register_model_view(ZabbixServerAssignment, 'bulk_delete')
class ZabbixServerAssignmentBulkDeleteView(BulkDeleteView):
    """
    ZabbixServerAssignment Object Bulk Delete view
    """

    queryset = ZabbixServerAssignment.objects.all()
    filterset = ZabbixServerAssignmentFilterSet
    table = ZabbixServerAssignmentTable
