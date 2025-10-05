from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView
from utilities.views import register_model_view

from nbxsync.choices import ZabbixHostInterfaceSNMPVersionChoices, ZabbixHostInterfaceTypeChoices, ZabbixInterfaceSNMPV3SecurityLevelChoices, ZabbixInterfaceUseChoices, ZabbixTLSChoices
from nbxsync.filtersets import ZabbixHostInterfaceFilterSet
from nbxsync.forms import ZabbixHostInterfaceBulkEditForm, ZabbixHostInterfaceFilterForm, ZabbixHostInterfaceForm
from nbxsync.models import ZabbixHostInterface
from nbxsync.tables import ZabbixHostInterfaceTable

__all__ = (
    'ZabbixHostInterfaceListView',
    'ZabbixHostInterfaceView',
    'ZabbixHostInterfaceEditView',
    'ZabbixHostInterfaceBulkEditView',
    'ZabbixHostInterfaceDeleteView',
    'ZabbixHostInterfaceBulkDeleteView',
)


# ZabbixHostInterface
@register_model_view(ZabbixHostInterface, name='list')
class ZabbixHostInterfaceListView(ObjectListView):
    """
    List view of all ZabbixHostInterface objects
    """

    queryset = ZabbixHostInterface.objects.all()
    table = ZabbixHostInterfaceTable
    filterset = ZabbixHostInterfaceFilterSet
    filterset_form = ZabbixHostInterfaceFilterForm


@register_model_view(ZabbixHostInterface)
class ZabbixHostInterfaceView(ObjectView):
    """
    ZabbixHostInterface object view
    """

    queryset = ZabbixHostInterface.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        context['ZabbixInterfaceUseChoices'] = ZabbixInterfaceUseChoices
        context['ZabbixHostInterfaceTypeChoices'] = ZabbixHostInterfaceTypeChoices
        context['ZabbixTLSChoices'] = ZabbixTLSChoices
        context['ZabbixHostInterfaceSNMPVersionChoices'] = ZabbixHostInterfaceSNMPVersionChoices
        context['ZabbixInterfaceSNMPV3SecurityLevelChoices'] = ZabbixInterfaceSNMPV3SecurityLevelChoices
        return context


@register_model_view(ZabbixHostInterface, 'edit')
class ZabbixHostInterfaceEditView(ObjectEditView):
    """
    ZabbixHostInterface Object Edit view
    """

    queryset = ZabbixHostInterface.objects.all()
    form = ZabbixHostInterfaceForm
    template_name = 'nbxsync/forms/zabbixhostinterface.html'


@register_model_view(ZabbixHostInterface, 'bulk_edit')
class ZabbixHostInterfaceBulkEditView(BulkEditView):
    """
    ZabbixHostInterface Object Bulk Edit view
    """

    queryset = ZabbixHostInterface.objects.all()
    filterset = ZabbixHostInterfaceFilterSet
    table = ZabbixHostInterfaceTable
    form = ZabbixHostInterfaceBulkEditForm


@register_model_view(ZabbixHostInterface, 'delete')
class ZabbixHostInterfaceDeleteView(ObjectDeleteView):
    queryset = ZabbixHostInterface.objects.all()


@register_model_view(ZabbixHostInterface, 'bulk_delete')
class ZabbixHostInterfaceBulkDeleteView(BulkDeleteView):
    """
    ZabbixHostInterface Object Bulk Delete view
    """

    queryset = ZabbixHostInterface.objects.all()
    filterset = ZabbixHostInterfaceFilterSet
    table = ZabbixHostInterfaceTable
