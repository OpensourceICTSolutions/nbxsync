from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixTemplateAssignmentSerializer
from nbxsync.filtersets import ZabbixTemplateAssignmentFilterSet
from nbxsync.models import ZabbixTemplateAssignment

__all__ = ('ZabbixTemplateAssignmentViewSet',)


class ZabbixTemplateAssignmentViewSet(NetBoxModelViewSet):
    queryset = ZabbixTemplateAssignment.objects.all()
    serializer_class = ZabbixTemplateAssignmentSerializer
    filterset_class = ZabbixTemplateAssignmentFilterSet
