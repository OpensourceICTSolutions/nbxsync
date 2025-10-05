from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixHostgroupAssignmentSerializer
from nbxsync.filtersets import ZabbixHostgroupAssignmentFilterSet
from nbxsync.models import ZabbixHostgroupAssignment

__all__ = ('ZabbixHostgroupAssignmentViewSet',)


class ZabbixHostgroupAssignmentViewSet(NetBoxModelViewSet):
    queryset = ZabbixHostgroupAssignment.objects.all()
    serializer_class = ZabbixHostgroupAssignmentSerializer
    filterset_class = ZabbixHostgroupAssignmentFilterSet
