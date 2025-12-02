from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixMacroAssignmentFilterSet
from nbxsync.forms import ZabbixMacroAssignmentBulkEditForm, ZabbixMacroAssignmentFilterForm, ZabbixMacroAssignmentForm
from nbxsync.models import ZabbixMacroAssignment
from nbxsync.tables import ZabbixMacroAssignmentTable

__all__ = (
    'ZabbixMacroAssignmentListView',
    'ZabbixMacroAssignmentView',
    'ZabbixMacroAssignmentEditView',
    'ZabbixMacroAssignmentBulkEditView',
    'ZabbixMacroAssignmentDeleteView',
    'ZabbixMacroAssignmentBulkDeleteView',
)


# ZabbixMacroAssignment
@register_model_view(ZabbixMacroAssignment, name='list')
class ZabbixMacroAssignmentListView(ObjectListView):
    """
    List view of all ZabbixMacroAssignment objects
    """

    queryset = ZabbixMacroAssignment.objects.all()
    table = ZabbixMacroAssignmentTable
    filterset = ZabbixMacroAssignmentFilterSet
    filterset_form = ZabbixMacroAssignmentFilterForm


@register_model_view(ZabbixMacroAssignment)
class ZabbixMacroAssignmentView(ObjectView):
    """
    ZabbixMacroAssignment object view
    """

    queryset = ZabbixMacroAssignment.objects.all()


@register_model_view(ZabbixMacroAssignment, 'edit')
class ZabbixMacroAssignmentEditView(ObjectEditView):
    """
    ZabbixMacroAssignment Object Edit view
    """

    queryset = ZabbixMacroAssignment.objects.all()
    form = ZabbixMacroAssignmentForm
    template_name = 'nbxsync/forms/zabbixmacroassignment.html'


@register_model_view(ZabbixMacroAssignment, 'bulk_edit')
class ZabbixMacroAssignmentBulkEditView(BulkEditView):
    """
    ZabbixMacroAssignment Object Bulk Edit view
    """

    queryset = ZabbixMacroAssignment.objects.all()
    filterset = ZabbixMacroAssignmentFilterSet
    table = ZabbixMacroAssignmentTable
    form = ZabbixMacroAssignmentBulkEditForm


@register_model_view(ZabbixMacroAssignment, 'delete')
class ZabbixMacroAssignmentDeleteView(ObjectDeleteView):
    queryset = ZabbixMacroAssignment.objects.all()


@register_model_view(ZabbixMacroAssignment, 'bulk_delete')
class ZabbixMacroAssignmentBulkDeleteView(BulkDeleteView):
    """
    ZabbixMacroAssignment Object Bulk Delete view
    """

    queryset = ZabbixMacroAssignment.objects.all()
    filterset = ZabbixMacroAssignmentFilterSet
    table = ZabbixMacroAssignmentTable
