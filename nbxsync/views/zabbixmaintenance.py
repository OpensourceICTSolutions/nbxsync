from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixMaintenanceFilterSet
from nbxsync.forms import ZabbixMaintenanceBulkEditForm, ZabbixMaintenanceFilterForm, ZabbixMaintenanceForm
from nbxsync.models import ZabbixMaintenance, ZabbixMaintenanceObjectAssignment, ZabbixMaintenancePeriod, ZabbixMaintenanceTagAssignment
from nbxsync.tables import ZabbixMaintenanceObjectAssignmentObjectViewTable, ZabbixMaintenancePeriodObjectViewTable, ZabbixMaintenanceTable, ZabbixMaintenanceTagAssignmentObjectViewTable


__all__ = ('ZabbixMaintenanceListView', 'ZabbixMaintenanceView', 'ZabbixMaintenanceEditView', 'ZabbixMaintenanceBulkEditView', 'ZabbixMaintenanceDeleteView', 'ZabbixMaintenanceBulkDeleteView')


# ZabbixMaintenance
@register_model_view(ZabbixMaintenance, name='list')
class ZabbixMaintenanceListView(ObjectListView):
    """
    List view of all ZabbixMaintenance objects
    """

    queryset = ZabbixMaintenance.objects.all()
    table = ZabbixMaintenanceTable
    filterset = ZabbixMaintenanceFilterSet
    filterset_form = ZabbixMaintenanceFilterForm


@register_model_view(ZabbixMaintenance)
class ZabbixMaintenanceView(ObjectView):
    """
    ZabbixMaintenance object view
    """

    queryset = ZabbixMaintenance.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        # Get all assignments where this template is used
        mainenance_periods = ZabbixMaintenancePeriod.objects.filter(zabbixmaintenance=instance)
        maintenanceobjectassignments = ZabbixMaintenanceObjectAssignment.objects.filter(zabbixmaintenance=instance)
        maintenancetagassignments = ZabbixMaintenanceTagAssignment.objects.filter(zabbixmaintenance=instance)

        if mainenance_periods:
            maintenanceperiod_table = ZabbixMaintenancePeriodObjectViewTable(mainenance_periods)
            maintenanceperiod_table.configure(request)
        else:
            maintenanceperiod_table = None

        if maintenanceobjectassignments:
            maintenanceobjectassignment_table = ZabbixMaintenanceObjectAssignmentObjectViewTable(maintenanceobjectassignments)
            maintenanceobjectassignment_table.configure(request)
        else:
            maintenanceobjectassignment_table = None

        if maintenancetagassignments:
            maintenancetagassignment_table = ZabbixMaintenanceTagAssignmentObjectViewTable(maintenancetagassignments)
            maintenancetagassignment_table.configure(request)
        else:
            maintenancetagassignment_table = None

        context['maintenanceperiod_table'] = maintenanceperiod_table
        context['maintenanceobjectassignment_table'] = maintenanceobjectassignment_table
        context['maintenancetagassignment_table'] = maintenancetagassignment_table
        return context


@register_model_view(ZabbixMaintenance, 'edit')
class ZabbixMaintenanceEditView(ObjectEditView):
    """
    ZabbixMaintenance Object Edit view
    """

    queryset = ZabbixMaintenance.objects.all()
    form = ZabbixMaintenanceForm


@register_model_view(ZabbixMaintenance, 'bulk_edit')
class ZabbixMaintenanceBulkEditView(BulkEditView):
    """
    ZabbixMaintenance Object Bulk Edit view
    """

    queryset = ZabbixMaintenance.objects.all()
    filterset = ZabbixMaintenanceFilterSet
    table = ZabbixMaintenanceTable
    form = ZabbixMaintenanceBulkEditForm


@register_model_view(ZabbixMaintenance, 'delete')
class ZabbixMaintenanceDeleteView(ObjectDeleteView):
    queryset = ZabbixMaintenance.objects.all()


@register_model_view(ZabbixMaintenance, 'bulk_delete')
class ZabbixMaintenanceBulkDeleteView(BulkDeleteView):
    """
    ZabbixMaintenance Object Bulk Delete view
    """

    queryset = ZabbixMaintenance.objects.all()
    filterset = ZabbixMaintenanceFilterSet
    table = ZabbixMaintenanceTable
