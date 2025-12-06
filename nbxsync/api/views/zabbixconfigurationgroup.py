from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixConfigurationGroupSerializer
from nbxsync.filtersets import ZabbixConfigurationGroupFilterSet
from nbxsync.models import ZabbixConfigurationGroup

__all__ = ('ZabbixConfigurationGroupViewSet',)


class ZabbixConfigurationGroupViewSet(NetBoxModelViewSet):
    queryset = ZabbixConfigurationGroup.objects.all()
    serializer_class = ZabbixConfigurationGroupSerializer
    filterset_class = ZabbixConfigurationGroupFilterSet
