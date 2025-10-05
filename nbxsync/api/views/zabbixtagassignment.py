from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixTagAssignmentSerializer
from nbxsync.filtersets import ZabbixTagAssignmentFilterSet
from nbxsync.models import ZabbixTagAssignment

__all__ = ('ZabbixTagAssignmentViewSet',)


class ZabbixTagAssignmentViewSet(NetBoxModelViewSet):
    queryset = ZabbixTagAssignment.objects.all()
    serializer_class = ZabbixTagAssignmentSerializer
    filterset_class = ZabbixTagAssignmentFilterSet
