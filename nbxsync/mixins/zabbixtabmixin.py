from nbxsync.utils import get_zabbixassignments_for_request
from utilities.views import ViewTab

__all__ = ('ZabbixTabMixin',)


class ZabbixTabMixin:
    template_name = 'nbxsync/tabs/minimal.html'
    tab = ViewTab(label='Zabbix')

    def get_extra_context(self, request, instance):
        return get_zabbixassignments_for_request(instance, request)
