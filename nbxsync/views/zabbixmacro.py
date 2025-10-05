from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixMacroFilterSet
from nbxsync.forms import ZabbixMacroBulkEditForm, ZabbixMacroFilterForm, ZabbixMacroForm
from nbxsync.models import ZabbixMacro, ZabbixMacroAssignment
from nbxsync.tables import ZabbixMacroAssignmentTable, ZabbixMacroTable

__all__ = (
    'ZabbixMacroListView',
    'ZabbixMacroView',
    'ZabbixMacroEditView',
    'ZabbixMacroBulkEditView',
    'ZabbixMacroDeleteView',
    'ZabbixMacroBulkDeleteView',
)


# ZabbixMacro
@register_model_view(ZabbixMacro, name='list')
class ZabbixMacroListView(ObjectListView):
    """
    List view of all ZabbixMacro objects
    """

    queryset = ZabbixMacro.objects.all()
    table = ZabbixMacroTable
    filterset = ZabbixMacroFilterSet
    filterset_form = ZabbixMacroFilterForm


@register_model_view(ZabbixMacro)
class ZabbixMacroView(ObjectView):
    """
    ZabbixMacro object view
    """

    queryset = ZabbixMacro.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        # Get all assignments where this template is used
        macro_assignments = ZabbixMacroAssignment.objects.filter(zabbixmacro=instance).select_related('assigned_object_type')

        if macro_assignments:
            objectassignment_table = ZabbixMacroAssignmentTable(macro_assignments)
            objectassignment_table.configure(request)
        else:
            objectassignment_table = None

        context['objectassignment_table'] = objectassignment_table
        return context


@register_model_view(ZabbixMacro, 'edit')
class ZabbixMacroEditView(ObjectEditView):
    """
    ZabbixMacro Object Edit view
    """

    queryset = ZabbixMacro.objects.all()
    form = ZabbixMacroForm


@register_model_view(ZabbixMacro, 'bulk_edit')
class ZabbixMacroBulkEditView(BulkEditView):
    """
    ZabbixMacro Object Bulk Edit view
    """

    queryset = ZabbixMacro.objects.all()
    filterset = ZabbixMacroFilterSet
    table = ZabbixMacroTable
    form = ZabbixMacroBulkEditForm


@register_model_view(ZabbixMacro, 'delete')
class ZabbixMacroDeleteView(ObjectDeleteView):
    queryset = ZabbixMacro.objects.all()


@register_model_view(ZabbixMacro, 'bulk_delete')
class ZabbixMacroBulkDeleteView(BulkDeleteView):
    """
    ZabbixMacro Object Bulk Delete view
    """

    queryset = ZabbixMacro.objects.all()
    filterset = ZabbixMacroFilterSet
    table = ZabbixMacroTable
