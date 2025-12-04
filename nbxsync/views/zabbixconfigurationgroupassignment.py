from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixConfigurationGroupAssignmentFilterSet
from nbxsync.forms import ZabbixConfigurationGroupAssignmentBulkEditForm, ZabbixConfigurationGroupAssignmentFilterForm, ZabbixConfigurationGroupAssignmentForm
from nbxsync.models import ZabbixConfigurationGroupAssignment
from nbxsync.tables import ZabbixConfigurationGroupAssignmentTable

__all__ = (
    'ZabbixConfigurationGroupAssignmentListView',
    'ZabbixConfigurationGroupAssignmentView',
    'ZabbixConfigurationGroupAssignmentEditView',
    'ZabbixConfigurationGroupAssignmentBulkEditView',
    'ZabbixConfigurationGroupAssignmentDeleteView',
    'ZabbixConfigurationGroupAssignmentBulkDeleteView',
)


# ZabbixConfigurationGroupAssignment
@register_model_view(ZabbixConfigurationGroupAssignment, name='list')
class ZabbixConfigurationGroupAssignmentListView(ObjectListView):
    """
    List view of all ZabbixConfigurationGroupAssignment objects
    """

    queryset = ZabbixConfigurationGroupAssignment.objects.all()
    table = ZabbixConfigurationGroupAssignmentTable
    filterset = ZabbixConfigurationGroupAssignmentFilterSet
    filterset_form = ZabbixConfigurationGroupAssignmentFilterForm


@register_model_view(ZabbixConfigurationGroupAssignment)
class ZabbixConfigurationGroupAssignmentView(ObjectView):
    """
    ZabbixConfigurationGroupAssignment object view
    """

    queryset = ZabbixConfigurationGroupAssignment.objects.all()


@register_model_view(ZabbixConfigurationGroupAssignment, 'edit')
class ZabbixConfigurationGroupAssignmentEditView(ObjectEditView):
    """
    ZabbixConfigurationGroupAssignment Object Edit view
    """

    queryset = ZabbixConfigurationGroupAssignment.objects.all()
    form = ZabbixConfigurationGroupAssignmentForm


@register_model_view(ZabbixConfigurationGroupAssignment, 'bulk_edit')
class ZabbixConfigurationGroupAssignmentBulkEditView(BulkEditView):
    """
    ZabbixConfigurationGroupAssignment Object Bulk Edit view
    """

    queryset = ZabbixConfigurationGroupAssignment.objects.all()
    filterset = ZabbixConfigurationGroupAssignmentFilterSet
    table = ZabbixConfigurationGroupAssignmentTable
    form = ZabbixConfigurationGroupAssignmentBulkEditForm


@register_model_view(ZabbixConfigurationGroupAssignment, 'delete')
class ZabbixConfigurationGroupAssignmentDeleteView(ObjectDeleteView):
    queryset = ZabbixConfigurationGroupAssignment.objects.all()


@register_model_view(ZabbixConfigurationGroupAssignment, 'bulk_delete')
class ZabbixConfigurationGroupAssignmentBulkDeleteView(BulkDeleteView):
    """
    ZabbixConfigurationGroupAssignment Object Bulk Delete view
    """

    queryset = ZabbixConfigurationGroupAssignment.objects.all()
    filterset = ZabbixConfigurationGroupAssignmentFilterSet
    table = ZabbixConfigurationGroupAssignmentTable
