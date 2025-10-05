from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixTagFilterSet
from nbxsync.forms import ZabbixTagBulkEditForm, ZabbixTagFilterForm, ZabbixTagForm
from nbxsync.models import ZabbixTag, ZabbixTagAssignment
from nbxsync.tables import ZabbixTagAssignmentTable, ZabbixTagTable

__all__ = ('ZabbixTagListView', 'ZabbixTagView', 'ZabbixTagEditView', 'ZabbixTagBulkEditView', 'ZabbixTagDeleteView', 'ZabbixTagBulkDeleteView')


# ZabbixTag
@register_model_view(ZabbixTag, name='list')
class ZabbixTagListView(ObjectListView):
    """
    List view of all ZabbixTag objects
    """

    queryset = ZabbixTag.objects.all()
    table = ZabbixTagTable
    filterset = ZabbixTagFilterSet
    filterset_form = ZabbixTagFilterForm


@register_model_view(ZabbixTag)
class ZabbixTagView(ObjectView):
    """
    ZabbixTag object view
    """

    queryset = ZabbixTag.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        # Get all assignments where this template is used
        assignments = ZabbixTagAssignment.objects.filter(zabbixtag=instance).select_related('assigned_object_type')

        if assignments:
            objectassignment_table = ZabbixTagAssignmentTable(assignments)
            objectassignment_table.configure(request)
        else:
            objectassignment_table = None

        context['objectassignment_table'] = objectassignment_table
        return context


@register_model_view(ZabbixTag, 'edit')
class ZabbixTagEditView(ObjectEditView):
    """
    ZabbixTag Object Edit view
    """

    queryset = ZabbixTag.objects.all()
    form = ZabbixTagForm


@register_model_view(ZabbixTag, 'bulk_edit')
class ZabbixTagBulkEditView(BulkEditView):
    """
    ZabbixTag Object Bulk Edit view
    """

    queryset = ZabbixTag.objects.all()
    filterset = ZabbixTagFilterSet
    table = ZabbixTagTable
    form = ZabbixTagBulkEditForm


@register_model_view(ZabbixTag, 'delete')
class ZabbixTagDeleteView(ObjectDeleteView):
    queryset = ZabbixTag.objects.all()


@register_model_view(ZabbixTag, 'bulk_delete')
class ZabbixTagBulkDeleteView(BulkDeleteView):
    """
    ZabbixTag Object Bulk Delete view
    """

    queryset = ZabbixTag.objects.all()
    filterset = ZabbixTagFilterSet
    table = ZabbixTagTable
