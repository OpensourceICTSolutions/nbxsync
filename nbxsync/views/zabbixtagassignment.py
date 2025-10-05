from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixTagAssignmentFilterSet
from nbxsync.forms import ZabbixTagAssignmentBulkEditForm, ZabbixTagAssignmentFilterForm, ZabbixTagAssignmentForm
from nbxsync.models import ZabbixTagAssignment
from nbxsync.tables import ZabbixTagAssignmentTable

__all__ = ('ZabbixTagAssignmentListView', 'ZabbixTagAssignmentView', 'ZabbixTagAssignmentEditView', 'ZabbixTagAssignmentBulkEditView', 'ZabbixTagAssignmentDeleteView', 'ZabbixTagAssignmentBulkDeleteView')


# ZabbixTagAssignment
@register_model_view(ZabbixTagAssignment, name='list')
class ZabbixTagAssignmentListView(ObjectListView):
    """
    List view of all ZabbixTagAssignment objects
    """

    queryset = ZabbixTagAssignment.objects.all()
    table = ZabbixTagAssignmentTable
    filterset = ZabbixTagAssignmentFilterSet
    filterset_form = ZabbixTagAssignmentFilterForm


@register_model_view(ZabbixTagAssignment)
class ZabbixTagAssignmentView(ObjectView):
    """
    ZabbixTagAssignment object view
    """

    queryset = ZabbixTagAssignment.objects.all()


@register_model_view(ZabbixTagAssignment, 'edit')
class ZabbixTagAssignmentEditView(ObjectEditView):
    """
    ZabbixTagAssignment Object Edit view
    """

    queryset = ZabbixTagAssignment.objects.all()
    form = ZabbixTagAssignmentForm


@register_model_view(ZabbixTagAssignment, 'bulk_edit')
class ZabbixTagAssignmentBulkEditView(BulkEditView):
    """
    ZabbixTagAssignment Object Bulk Edit view
    """

    queryset = ZabbixTagAssignment.objects.all()
    filterset = ZabbixTagAssignmentFilterSet
    table = ZabbixTagAssignmentTable
    form = ZabbixTagAssignmentBulkEditForm


@register_model_view(ZabbixTagAssignment, 'delete')
class ZabbixTagAssignmentDeleteView(ObjectDeleteView):
    queryset = ZabbixTagAssignment.objects.all()


@register_model_view(ZabbixTagAssignment, 'bulk_delete')
class ZabbixTagAssignmentBulkDeleteView(BulkDeleteView):
    """
    ZabbixTagAssignment Object Bulk Delete view
    """

    queryset = ZabbixTagAssignment.objects.all()
    filterset = ZabbixTagAssignmentFilterSet
    table = ZabbixTagAssignmentTable
