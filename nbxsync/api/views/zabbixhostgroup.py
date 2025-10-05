from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixHostgroupSerializer
from nbxsync.filtersets import ZabbixHostgroupFilterSet
from nbxsync.models import ZabbixHostgroup

__all__ = ('ZabbixHostgroupViewSet',)


class ZabbixHostgroupViewSet(NetBoxModelViewSet):
    queryset = ZabbixHostgroup.objects.all()
    serializer_class = ZabbixHostgroupSerializer
    filterset_class = ZabbixHostgroupFilterSet
