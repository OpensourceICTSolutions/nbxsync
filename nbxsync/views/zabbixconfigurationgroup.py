from django.contrib.contenttypes.models import ContentType

from netbox.views.generic import BulkDeleteView, BulkImportView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixConfigurationGroupFilterSet
from nbxsync.forms import ZabbixConfigurationGroupBulkEditForm, ZabbixConfigurationGroupFilterForm, ZabbixConfigurationGroupForm, ZabbixConfigurationGroupBulkImportForm
from nbxsync.models import ZabbixConfigurationGroup, ZabbixHostInterface, ZabbixConfigurationGroupAssignment, ZabbixServerAssignment
from nbxsync.tables import ZabbixConfigurationGroupTable, ZabbixHostInterfaceObjectViewTable, ZabbixConfigurationGroupAssignmentDetailViewTable, ZabbixServerAssignmentObjectViewTable
from nbxsync.utils import get_zabbixassignments_for_request


__all__ = (
    'ZabbixConfigurationGroupListView',
    'ZabbixConfigurationGroupView',
    'ZabbixConfigurationGroupBulkImportView',
    'ZabbixConfigurationGroupEditView',
    'ZabbixConfigurationGroupBulkEditView',
    'ZabbixConfigurationGroupDeleteView',
    'ZabbixConfigurationGroupBulkDeleteView',
)


# ZabbixConfigurationGroup
@register_model_view(ZabbixConfigurationGroup, name='list')
class ZabbixConfigurationGroupListView(ObjectListView):
    """
    List view of all ZabbixConfigurationGroup objects
    """

    queryset = ZabbixConfigurationGroup.objects.all()
    table = ZabbixConfigurationGroupTable
    filterset = ZabbixConfigurationGroupFilterSet
    filterset_form = ZabbixConfigurationGroupFilterForm


@register_model_view(ZabbixConfigurationGroup)
class ZabbixConfigurationGroupView(ObjectView):
    """
    ZabbixConfigurationGroup object view
    """

    queryset = ZabbixConfigurationGroup.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        object_assignments = get_zabbixassignments_for_request(instance, request)

        # Get all assignments where this template is used
        object_ct = ContentType.objects.get_for_model(instance)
        hostinterface_assignments = ZabbixHostInterface.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).select_related('assigned_object_type')
        objectassignments = ZabbixConfigurationGroupAssignment.objects.filter(zabbixconfigurationgroup=instance.pk).select_related('assigned_object_type')
        zabbixserver_assignments = ZabbixServerAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).select_related('assigned_object_type')

        if hostinterface_assignments:
            hostinterface_assignment_table = ZabbixHostInterfaceObjectViewTable(hostinterface_assignments)
            hostinterface_assignment_table.configure(request)
        else:
            hostinterface_assignment_table = None

        if objectassignments:
            objectassignments_table = ZabbixConfigurationGroupAssignmentDetailViewTable(objectassignments)
            objectassignments_table.configure(request)
        else:
            objectassignments_table = None

        if zabbixserver_assignments:
            zabbixserver_assignments_table = ZabbixServerAssignmentObjectViewTable(zabbixserver_assignments)
            zabbixserver_assignments_table.configure(request)
        else:
            zabbixserver_assignments_table = None

        context['hostinterface_assignment_table'] = hostinterface_assignment_table
        context['objectassignments_table'] = objectassignments_table
        context['zabbixserver_assignments_table'] = zabbixserver_assignments_table

        return context | object_assignments


@register_model_view(ZabbixConfigurationGroup, 'edit')
class ZabbixConfigurationGroupEditView(ObjectEditView):
    """
    ZabbixConfigurationGroup Object Edit view
    """

    queryset = ZabbixConfigurationGroup.objects.all()
    form = ZabbixConfigurationGroupForm


@register_model_view(ZabbixConfigurationGroup, 'bulk_import')
class ZabbixConfigurationGroupBulkImportView(BulkImportView):
    queryset = ZabbixConfigurationGroup.objects.all()
    model_form = ZabbixConfigurationGroupBulkImportForm
    table = ZabbixConfigurationGroupTable


@register_model_view(ZabbixConfigurationGroup, 'bulk_edit')
class ZabbixConfigurationGroupBulkEditView(BulkEditView):
    """
    ZabbixConfigurationGroup Object Bulk Edit view
    """

    queryset = ZabbixConfigurationGroup.objects.all()
    filterset = ZabbixConfigurationGroupFilterSet
    table = ZabbixConfigurationGroupTable
    form = ZabbixConfigurationGroupBulkEditForm


@register_model_view(ZabbixConfigurationGroup, 'delete')
class ZabbixConfigurationGroupDeleteView(ObjectDeleteView):
    queryset = ZabbixConfigurationGroup.objects.all()


@register_model_view(ZabbixConfigurationGroup, 'bulk_delete')
class ZabbixConfigurationGroupBulkDeleteView(BulkDeleteView):
    """
    ZabbixConfigurationGroup Object Bulk Delete view
    """

    queryset = ZabbixConfigurationGroup.objects.all()
    filterset = ZabbixConfigurationGroupFilterSet
    table = ZabbixConfigurationGroupTable
