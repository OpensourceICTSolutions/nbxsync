from django.db.models import Count
from netbox.views.generic import BulkDeleteView, BulkImportView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixHostgroupFilterSet
from nbxsync.forms import ZabbixHostgroupBulkEditForm, ZabbixHostgroupFilterForm, ZabbixHostgroupForm, ZabbixHostgroupBulkImportForm
from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixTemplateRule
from nbxsync.tables import ZabbixHostgroupObjectViewTable, ZabbixHostgroupTable, ZabbixTemplateRuleHostgroupViewTable

__all__ = (
    'ZabbixHostgroupListView',
    'ZabbixHostgroupView',
    'ZabbixHostgroupBulkImportView',
    'ZabbixHostgroupEditView',
    'ZabbixHostgroupBulkEditView',
    'ZabbixHostgroupDeleteView',
    'ZabbixHostgroupBulkDeleteView',
)


# ZabbixHostgroup
@register_model_view(ZabbixHostgroup, name='list')
class ZabbixHostgroupListView(ObjectListView):
    """
    List view of all ZabbixHostgroup objects
    """

    queryset = ZabbixHostgroup.objects.all()
    table = ZabbixHostgroupTable
    filterset = ZabbixHostgroupFilterSet
    filterset_form = ZabbixHostgroupFilterForm

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                assignment_count=Count('zabbixhostgroupassignment', distinct=True),
                rule_count=Count('zabbixtemplaterules', distinct=True),
            )
        )


@register_model_view(ZabbixHostgroup)
class ZabbixHostgroupView(ObjectView):
    """
    ZabbixHostgroup object view
    """

    queryset = ZabbixHostgroup.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        # Direct assignments (Sites/Roles Jinja, Priority tags, …)
        hostgroupassignments = ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=instance)

        if hostgroupassignments:
            hostgroupassignment_table = ZabbixHostgroupObjectViewTable(hostgroupassignments)
            hostgroupassignment_table.configure(request)
        else:
            hostgroupassignment_table = None

        # TemplateRules that attach this hostgroup when a platform (and optional
        # tags) match — e.g. OS/Linux via the Linux TemplateRule. This is a
        # second, first-class path; empty "Assigned objects" does not mean unused.
        templaterules = ZabbixTemplateRule.objects.filter(zabbixhostgroup=instance).select_related(
            'zabbixtemplate',
        )
        if templaterules.exists():
            templaterule_table = ZabbixTemplateRuleHostgroupViewTable(templaterules)
            templaterule_table.configure(request)
        else:
            templaterule_table = None

        context['hostgroupassignment_table'] = hostgroupassignment_table
        context['templaterule_table'] = templaterule_table
        return context


@register_model_view(ZabbixHostgroup, 'edit')
class ZabbixHostgroupEditView(ObjectEditView):
    """
    ZabbixHostgroup Object Edit view
    """

    queryset = ZabbixHostgroup.objects.all()
    form = ZabbixHostgroupForm


@register_model_view(ZabbixHostgroup, 'bulk_import')
class ZabbixHostgroupBulkImportView(BulkImportView):
    queryset = ZabbixHostgroup.objects.all()
    model_form = ZabbixHostgroupBulkImportForm
    table = ZabbixHostgroupTable


@register_model_view(ZabbixHostgroup, 'bulk_edit')
class ZabbixHostgroupBulkEditView(BulkEditView):
    """
    ZabbixHostgroup Object Bulk Edit view
    """

    queryset = ZabbixHostgroup.objects.all()
    filterset = ZabbixHostgroupFilterSet
    table = ZabbixHostgroupTable
    form = ZabbixHostgroupBulkEditForm


@register_model_view(ZabbixHostgroup, 'delete')
class ZabbixHostgroupDeleteView(ObjectDeleteView):
    queryset = ZabbixHostgroup.objects.all()


@register_model_view(ZabbixHostgroup, 'bulk_delete')
class ZabbixHostgroupBulkDeleteView(BulkDeleteView):
    """
    ZabbixHostgroup Object Bulk Delete view
    """

    queryset = ZabbixHostgroup.objects.all()
    filterset = ZabbixHostgroupFilterSet
    table = ZabbixHostgroupTable
