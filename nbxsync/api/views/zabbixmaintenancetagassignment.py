from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixMaintenanceTagAssignmentSerializer
from nbxsync.filtersets import ZabbixMaintenanceTagAssignmentFilterSet
from nbxsync.models import ZabbixMaintenanceTagAssignment

__all__ = ('ZabbixMaintenanceTagAssignmentViewSet',)


class ZabbixMaintenanceTagAssignmentViewSet(NetBoxModelViewSet):
    queryset = ZabbixMaintenanceTagAssignment.objects.all()
    serializer_class = ZabbixMaintenanceTagAssignmentSerializer
    filterset_class = ZabbixMaintenanceTagAssignmentFilterSet
