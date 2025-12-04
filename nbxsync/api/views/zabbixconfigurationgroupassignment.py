from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixConfigurationGroupAssignmentSerializer
from nbxsync.filtersets import ZabbixConfigurationGroupAssignmentFilterSet
from nbxsync.models import ZabbixConfigurationGroupAssignment

__all__ = ('ZabbixConfigurationGroupAssignmentViewSet',)


class ZabbixConfigurationGroupAssignmentViewSet(NetBoxModelViewSet):
    queryset = ZabbixConfigurationGroupAssignment.objects.all()
    serializer_class = ZabbixConfigurationGroupAssignmentSerializer
    filterset_class = ZabbixConfigurationGroupAssignmentFilterSet
