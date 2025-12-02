from django.contrib.contenttypes.models import ContentType

from netbox.views.generic import ObjectChildrenView, ObjectView
from utilities.views import register_model_view, ViewTab
from dcim.models import Device, VirtualDeviceContext, DeviceRole, DeviceType, Manufacturer, Platform
from virtualization.models import Cluster, ClusterType, VirtualMachine

from nbxsync.filtersets import ZabbixTemplateFilterSet, ZabbixMacroFilterSet
from nbxsync.mixins import ZabbixTabMixin
from nbxsync.models import ZabbixServer, ZabbixMacro, ZabbixHostInterface, ZabbixTemplate, ZabbixServerAssignment, ZabbixMaintenanceObjectAssignment, ZabbixHostInventory, ZabbixConfigurationGroupAssignment
from nbxsync.tables import ZabbixTemplateTable, ZabbixMacroTable, ZabbixHostInterfaceObjectViewTable, ZabbixServerAssignmentObjectViewTable, ZabbixMaintenanceObjectAssignmentDetailViewTable


@register_model_view(ZabbixServer, name='zabbixserver_templates', path='templates')
class ZabbixServerTemplatesView(ObjectChildrenView):
    queryset = ZabbixServer.objects.all()
    child_model = ZabbixTemplate
    table = ZabbixTemplateTable
    filterset = ZabbixTemplateFilterSet

    def get_children(self, request, parent):
        return ZabbixTemplate.objects.filter(zabbixserver=parent)

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        # Get all Templates linked to this ZabbixServer
        template_count = ZabbixTemplate.objects.filter(zabbixserver=instance).count()

        context['template_count'] = template_count

        return context


@register_model_view(ZabbixTemplate, name='zabbixtemplate_macros', path='macros')
class ZabbixTemplateMacrosView(ObjectChildrenView):
    queryset = ZabbixTemplate.objects.all()
    child_model = ZabbixMacro
    table = ZabbixMacroTable
    filterset = ZabbixMacroFilterSet

    def get_children(self, request, parent):
        object_ct = ContentType.objects.get_for_model(parent)
        return ZabbixMacro.objects.filter(assigned_object_type=object_ct, assigned_object_id=parent.id)

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        object_ct = ContentType.objects.get_for_model(instance)

        # Get all Macros linked to this ZabbixTemplate
        macro_count = ZabbixMacro.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.id).count()

        context['macro_count'] = macro_count

        return context


@register_model_view(Manufacturer, name='zabbix', path='zabbix')
class ZabbixManufacturerTabView(ZabbixTabMixin, ObjectView):
    queryset = Manufacturer.objects.all()


@register_model_view(DeviceType, name='zabbix', path='zabbix')
class ZabbixDeviceTypeTabView(ZabbixTabMixin, ObjectView):
    queryset = DeviceType.objects.all()


@register_model_view(DeviceRole, name='zabbix', path='zabbix')
class ZabbixDeviceRoleTabView(ZabbixTabMixin, ObjectView):
    queryset = DeviceRole.objects.all()


@register_model_view(Platform, name='zabbix', path='zabbix')
class ZabbixPlatformTabView(ZabbixTabMixin, ObjectView):
    queryset = Platform.objects.all()


@register_model_view(Cluster, name='zabbix', path='zabbix')
class ZabbixClusterTabView(ZabbixTabMixin, ObjectView):
    queryset = Cluster.objects.all()


@register_model_view(ClusterType, name='zabbix', path='zabbix')
class ZabbixClusterTypeTabView(ZabbixTabMixin, ObjectView):
    queryset = ClusterType.objects.all()


@register_model_view(Device, name='zabbix', path='zabbix')
class ZabbixDeviceTabView(ZabbixTabMixin, ObjectView):
    queryset = Device.objects.all()
    template_name = 'nbxsync/tabs/full.html'
    tab = ViewTab(label='Zabbix', badge=lambda obj: ZabbixServerAssignment.objects.filter(assigned_object_type=ContentType.objects.get_for_model(obj), assigned_object_id=obj.pk).count(), permission='nbxsync.view_zabbixserver')

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        # Get all assignments where this template is used
        object_ct = ContentType.objects.get_for_model(instance)
        hostinterface_assignments = ZabbixHostInterface.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).select_related('assigned_object_type')
        zabbixserver_assignments = ZabbixServerAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).select_related('assigned_object_type')
        maintenance_objectassignments = ZabbixMaintenanceObjectAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).select_related('assigned_object_type')
        hostinventory_assignment = ZabbixHostInventory.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).first()
        configurationgroup_assignment = ZabbixConfigurationGroupAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).first()

        if hostinterface_assignments:
            hostinterface_assignment_table = ZabbixHostInterfaceObjectViewTable(hostinterface_assignments)
            hostinterface_assignment_table.configure(request)
        else:
            hostinterface_assignment_table = None

        if zabbixserver_assignments:
            zabbixserver_assignments_table = ZabbixServerAssignmentObjectViewTable(zabbixserver_assignments)
            zabbixserver_assignments_table.configure(request)
        else:
            zabbixserver_assignments_table = None

        if maintenance_objectassignments:
            maintenance_objectassignment_table = ZabbixMaintenanceObjectAssignmentDetailViewTable(maintenance_objectassignments)
            maintenance_objectassignment_table.configure(request)
        else:
            maintenance_objectassignment_table = None

        context['hostinterface_assignment_table'] = hostinterface_assignment_table
        context['zabbixserver_assignments_table'] = zabbixserver_assignments_table
        context['maintenance_objectassignment_table'] = maintenance_objectassignment_table
        context['hostinventory_assignment'] = hostinventory_assignment
        context['configurationgroup_assignment'] = configurationgroup_assignment
        return context


@register_model_view(VirtualMachine, name='zabbix', path='zabbix')
class ZabbixVirtualMachineTabView(ZabbixTabMixin, ObjectView):
    queryset = VirtualMachine.objects.all()
    template_name = 'nbxsync/tabs/full.html'
    tab = ViewTab(label='Zabbix', badge=lambda obj: ZabbixServerAssignment.objects.filter(assigned_object_type=ContentType.objects.get_for_model(obj), assigned_object_id=obj.pk).count(), permission='nbxsync.view_zabbixserver')

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        # Get all assignments where this template is used
        object_ct = ContentType.objects.get_for_model(instance)
        hostinterface_assignments = ZabbixHostInterface.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).select_related('assigned_object_type')
        zabbixserver_assignments = ZabbixServerAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).select_related('assigned_object_type')
        maintenance_objectassignments = ZabbixMaintenanceObjectAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).select_related('assigned_object_type')
        hostinventory_assignment = ZabbixHostInventory.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).first()
        configurationgroup_assignment = ZabbixConfigurationGroupAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).first()

        if hostinterface_assignments:
            hostinterface_assignment_table = ZabbixHostInterfaceObjectViewTable(hostinterface_assignments)
            hostinterface_assignment_table.configure(request)
        else:
            hostinterface_assignment_table = None

        if zabbixserver_assignments:
            zabbixserver_assignments_table = ZabbixServerAssignmentObjectViewTable(zabbixserver_assignments)
            zabbixserver_assignments_table.configure(request)
        else:
            zabbixserver_assignments_table = None

        if maintenance_objectassignments:
            maintenance_objectassignment_table = ZabbixMaintenanceObjectAssignmentDetailViewTable(maintenance_objectassignments)
            maintenance_objectassignment_table.configure(request)
        else:
            maintenance_objectassignment_table = None

        context['hostinterface_assignment_table'] = hostinterface_assignment_table
        context['zabbixserver_assignments_table'] = zabbixserver_assignments_table
        context['maintenance_objectassignment_table'] = maintenance_objectassignment_table
        context['hostinventory_assignment'] = hostinventory_assignment
        context['configurationgroup_assignment'] = configurationgroup_assignment

        return context


@register_model_view(VirtualDeviceContext, name='zabbix', path='zabbix')
class ZabbixVirtualDeviceContextTabView(ZabbixTabMixin, ObjectView):
    queryset = VirtualDeviceContext.objects.all()
    template_name = 'nbxsync/tabs/full.html'
    tab = ViewTab(label='Zabbix', badge=lambda obj: ZabbixServerAssignment.objects.filter(assigned_object_type=ContentType.objects.get_for_model(obj), assigned_object_id=obj.pk).count(), permission='nbxsync.view_zabbixserver')

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        # Get all assignments where this template is used
        object_ct = ContentType.objects.get_for_model(instance)
        hostinterface_assignments = ZabbixHostInterface.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).select_related('assigned_object_type')
        zabbixserver_assignments = ZabbixServerAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).select_related('assigned_object_type')
        maintenance_objectassignments = ZabbixMaintenanceObjectAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).select_related('assigned_object_type')
        hostinventory_assignment = ZabbixHostInventory.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).first()
        configurationgroup_assignment = ZabbixConfigurationGroupAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=instance.pk).first()

        if hostinterface_assignments:
            hostinterface_assignment_table = ZabbixHostInterfaceObjectViewTable(hostinterface_assignments)
            hostinterface_assignment_table.configure(request)
        else:
            hostinterface_assignment_table = None

        if zabbixserver_assignments:
            zabbixserver_assignments_table = ZabbixServerAssignmentObjectViewTable(zabbixserver_assignments)
            zabbixserver_assignments_table.configure(request)
        else:
            zabbixserver_assignments_table = None

        if maintenance_objectassignments:
            maintenance_objectassignment_table = ZabbixMaintenanceObjectAssignmentDetailViewTable(maintenance_objectassignments)
            maintenance_objectassignment_table.configure(request)
        else:
            maintenance_objectassignment_table = None

        context['hostinterface_assignment_table'] = hostinterface_assignment_table
        context['zabbixserver_assignments_table'] = zabbixserver_assignments_table
        context['maintenance_objectassignment_table'] = maintenance_objectassignment_table
        context['hostinventory_assignment'] = hostinventory_assignment
        context['configurationgroup_assignment'] = configurationgroup_assignment

        return context


#### Zabbix OPS


@register_model_view(Device, name='zabbix_ops', path='zabbix_ops')
class ZabbixDeviceOpsTabView(ZabbixTabMixin, ObjectView):
    queryset = Device.objects.all()
    template_name = 'nbxsync/tabs/ops.html'
    tab = ViewTab(label='Zabbix Ops', permission='nbxsync.view_zabbixserver')


@register_model_view(VirtualDeviceContext, name='zabbix_ops', path='zabbix_ops')
class ZabbixVirtualMachineOpsTabView(ZabbixTabMixin, ObjectView):
    queryset = VirtualDeviceContext.objects.all()
    template_name = 'nbxsync/tabs/ops.html'
    tab = ViewTab(label='Zabbix Ops', permission='nbxsync.view_zabbixserver')


@register_model_view(VirtualMachine, name='zabbix_ops', path='zabbix_ops')
class ZabbixVirtualMachineOpsTabView(ZabbixTabMixin, ObjectView):
    queryset = VirtualMachine.objects.all()
    template_name = 'nbxsync/tabs/ops.html'
    tab = ViewTab(label='Zabbix Ops', permission='nbxsync.view_zabbixserver')
