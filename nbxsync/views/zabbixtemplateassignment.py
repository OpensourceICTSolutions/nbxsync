from netbox.views.generic import BulkDeleteView, BulkImportView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixTemplateAssignmentFilterSet
from nbxsync.forms import ZabbixTemplateAssignmentFilterForm, ZabbixTemplateAssignmentForm
from nbxsync.models import ZabbixTemplateAssignment
from nbxsync.tables import ZabbixTemplateAssignmentTable

__all__ = ('ZabbixTemplateAssignmentListView', 'ZabbixTemplateAssignmentView', 'ZabbixTemplateAssignmentEditView', 'ZabbixTemplateAssignmentDeleteView')


# ZabbixTemplateAssignment
@register_model_view(ZabbixTemplateAssignment, name='list')
class ZabbixTemplateAssignmentListView(ObjectListView):
    """
    List view of all ZabbixTemplateAssignment objects
    """

    queryset = ZabbixTemplateAssignment.objects.all()
    table = ZabbixTemplateAssignmentTable
    filterset = ZabbixTemplateAssignmentFilterSet
    filterset_form = ZabbixTemplateAssignmentFilterForm


@register_model_view(ZabbixTemplateAssignment)
class ZabbixTemplateAssignmentView(ObjectView):
    """
    ZabbixTemplateAssignment object view
    """

    queryset = ZabbixTemplateAssignment.objects.all()


@register_model_view(ZabbixTemplateAssignment, 'edit')
class ZabbixTemplateAssignmentEditView(ObjectEditView):
    """
    ZabbixTemplateAssignment Object Edit view
    """

    queryset = ZabbixTemplateAssignment.objects.all()
    form = ZabbixTemplateAssignmentForm


@register_model_view(ZabbixTemplateAssignment, 'delete')
class ZabbixTemplateAssignmentDeleteView(ObjectDeleteView):
    queryset = ZabbixTemplateAssignment.objects.all()
