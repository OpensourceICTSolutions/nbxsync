from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixMacroAssignmentSerializer
from nbxsync.filtersets import ZabbixMacroAssignmentFilterSet
from nbxsync.models import ZabbixMacroAssignment

__all__ = ('ZabbixMacroAssignmentViewSet',)


class ZabbixMacroAssignmentViewSet(NetBoxModelViewSet):
    queryset = ZabbixMacroAssignment.objects.all()
    serializer_class = ZabbixMacroAssignmentSerializer
    filterset_class = ZabbixMacroAssignmentFilterSet
