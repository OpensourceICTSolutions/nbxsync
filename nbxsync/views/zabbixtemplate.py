from django.contrib.contenttypes.models import ContentType

from netbox.views.generic import BulkDeleteView, BulkImportView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixTemplateFilterSet
from nbxsync.forms import ZabbixTemplateBulkImportForm, ZabbixTemplateBulkEditForm, ZabbixTemplateFilterForm, ZabbixTemplateForm
from nbxsync.models import ZabbixTemplate, ZabbixTemplateAssignment, ZabbixMacro
from nbxsync.tables import ZabbixTemplateAssignmentTable, ZabbixTemplateTable

__all__ = ('ZabbixTemplateListView', 'ZabbixTemplateView', 'ZabbixTemplateEditView', 'ZabbixTemplateBulkImportView', 'ZabbixTemplateBulkEditView', 'ZabbixTemplateDeleteView', 'ZabbixTemplateBulkDeleteView')


# ZabbixTemplate
@register_model_view(ZabbixTemplate, name='list')
class ZabbixTemplateListView(ObjectListView):
    """
    List view of all ZabbixTemplate objects
    """

    queryset = ZabbixTemplate.objects.all()
    table = ZabbixTemplateTable
    filterset = ZabbixTemplateFilterSet
    filterset_form = ZabbixTemplateFilterForm


@register_model_view(ZabbixTemplate)
class ZabbixTemplateView(ObjectView):
    """
    ZabbixTemplate object view
    """

    queryset = ZabbixTemplate.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        object_ct = ContentType.objects.get_for_model(instance)

        # Get all assignments where this template is used
        templateassignments = ZabbixTemplateAssignment.objects.filter(zabbixtemplate=instance).select_related('assigned_object_type')
        macro_count = ZabbixMacro.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.id).count()

        if templateassignments:
            objectassignment_table = ZabbixTemplateAssignmentTable(templateassignments)
            objectassignment_table.configure(request)
        else:
            objectassignment_table = None

        context['objectassignment_table'] = objectassignment_table
        context['macro_count'] = macro_count

        return context


@register_model_view(ZabbixTemplate, 'edit')
class ZabbixTemplateEditView(ObjectEditView):
    """
    ZabbixTemplate Object Edit view
    """

    queryset = ZabbixTemplate.objects.all()
    form = ZabbixTemplateForm


@register_model_view(ZabbixTemplate, 'bulk_import')
class ZabbixTemplateBulkImportView(BulkImportView):
    queryset = ZabbixTemplate.objects.all()
    model_form = ZabbixTemplateBulkImportForm
    table = ZabbixTemplateTable


@register_model_view(ZabbixTemplate, 'bulk_edit')
class ZabbixTemplateBulkEditView(BulkEditView):
    """
    ZabbixTemplate Object Bulk Edit view
    """

    queryset = ZabbixTemplate.objects.all()
    filterset = ZabbixTemplateFilterSet
    table = ZabbixTemplateTable
    form = ZabbixTemplateBulkEditForm


@register_model_view(ZabbixTemplate, 'delete')
class ZabbixTemplateDeleteView(ObjectDeleteView):
    queryset = ZabbixTemplate.objects.all()


@register_model_view(ZabbixTemplate, 'bulk_delete')
class ZabbixTemplateBulkDeleteView(BulkDeleteView):
    """
    ZabbixTemplate Object Bulk Delete view
    """

    queryset = ZabbixTemplate.objects.all()
    filterset = ZabbixTemplateFilterSet
    table = ZabbixTemplateTable
