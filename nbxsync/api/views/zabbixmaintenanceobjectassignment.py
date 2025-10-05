from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixMaintenanceObjectAssignmentSerializer
from nbxsync.filtersets import ZabbixMaintenanceObjectAssignmentFilterSet
from nbxsync.models import ZabbixMaintenanceObjectAssignment

__all__ = ('ZabbixMaintenanceObjectAssignmentViewSet',)


class ZabbixMaintenanceObjectAssignmentViewSet(NetBoxModelViewSet):
    queryset = ZabbixMaintenanceObjectAssignment.objects.all()
    serializer_class = ZabbixMaintenanceObjectAssignmentSerializer
    filterset_class = ZabbixMaintenanceObjectAssignmentFilterSet
