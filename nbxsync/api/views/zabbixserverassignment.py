from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixServerAssignmentSerializer
from nbxsync.filtersets import ZabbixServerAssignmentFilterSet
from nbxsync.models import ZabbixServerAssignment

__all__ = ('ZabbixServerAssignmentViewSet',)


class ZabbixServerAssignmentViewSet(NetBoxModelViewSet):
    queryset = ZabbixServerAssignment.objects.all()
    serializer_class = ZabbixServerAssignmentSerializer
    filterset_class = ZabbixServerAssignmentFilterSet
