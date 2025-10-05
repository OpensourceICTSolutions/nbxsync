from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixHostgroupAssignmentFilterSet
from nbxsync.forms import ZabbixHostgroupAssignmentBulkEditForm, ZabbixHostgroupAssignmentFilterForm, ZabbixHostgroupAssignmentForm
from nbxsync.models import ZabbixHostgroupAssignment
from nbxsync.tables import ZabbixHostgroupAssignmentTable

__all__ = (
    'ZabbixHostgroupAssignmentListView',
    'ZabbixHostgroupAssignmentView',
    'ZabbixHostgroupAssignmentEditView',
    'ZabbixHostgroupAssignmentBulkEditView',
    'ZabbixHostgroupAssignmentDeleteView',
    'ZabbixHostgroupAssignmentBulkDeleteView',
)


# ZabbixHostgroupAssignment
@register_model_view(ZabbixHostgroupAssignment, name='list')
class ZabbixHostgroupAssignmentListView(ObjectListView):
    """
    List view of all ZabbixHostgroupAssignment objects
    """

    queryset = ZabbixHostgroupAssignment.objects.all()
    table = ZabbixHostgroupAssignmentTable
    filterset = ZabbixHostgroupAssignmentFilterSet
    filterset_form = ZabbixHostgroupAssignmentFilterForm


@register_model_view(ZabbixHostgroupAssignment)
class ZabbixHostgroupAssignmentView(ObjectView):
    """
    ZabbixHostgroupAssignment object view
    """

    queryset = ZabbixHostgroupAssignment.objects.all()


@register_model_view(ZabbixHostgroupAssignment, 'edit')
class ZabbixHostgroupAssignmentEditView(ObjectEditView):
    """
    ZabbixHostgroupAssignment Object Edit view
    """

    queryset = ZabbixHostgroupAssignment.objects.all()
    form = ZabbixHostgroupAssignmentForm


@register_model_view(ZabbixHostgroupAssignment, 'bulk_edit')
class ZabbixHostgroupAssignmentBulkEditView(BulkEditView):
    """
    ZabbixHostgroupAssignment Object Bulk Edit view
    """

    queryset = ZabbixHostgroupAssignment.objects.all()
    filterset = ZabbixHostgroupAssignmentFilterSet
    table = ZabbixHostgroupAssignmentTable
    form = ZabbixHostgroupAssignmentBulkEditForm


@register_model_view(ZabbixHostgroupAssignment, 'delete')
class ZabbixHostgroupAssignmentDeleteView(ObjectDeleteView):
    queryset = ZabbixHostgroupAssignment.objects.all()


@register_model_view(ZabbixHostgroupAssignment, 'bulk_delete')
class ZabbixHostgroupAssignmentBulkDeleteView(BulkDeleteView):
    """
    ZabbixHostgroupAssignment Object Bulk Delete view
    """

    queryset = ZabbixHostgroupAssignment.objects.all()
    filterset = ZabbixHostgroupAssignmentFilterSet
    table = ZabbixHostgroupAssignmentTable
