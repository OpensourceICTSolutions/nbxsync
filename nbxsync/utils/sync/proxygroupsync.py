from .syncbase import ZabbixSyncBase


class ProxyGroupSync(ZabbixSyncBase):
    id_field = 'proxy_groupid'
    sot_key = 'proxygroup'

    def api_object(self):
        return self.api.proxygroup

    def get_create_params(self):
        return {
            'name': self.obj.name,
            'description': self.obj.description,
            'failover_delay': self.obj.failover_delay,
            'min_online': self.obj.min_online,
        }

    def get_update_params(self, **kwargs):
        return {
            'proxy_groupid': self.obj.proxy_groupid,
            'name': self.obj.name,
            'description': self.obj.description,
            'failover_delay': self.obj.failover_delay,
            'min_online': self.obj.min_online,
        }

    def result_key(self):
        return 'proxy_groupids'

    def sync_from_zabbix(self, data):
        try:
            self.obj.proxy_groupid = data['proxy_groupid']
            self.obj.name = data.get('name', self.obj.name)
            self.obj.description = data.get('description', '')
            self.obj.failover_delay = data.get('failover_delay')
            self.obj.min_online = data.get('min_online')
            self.obj.save()
            self.obj.update_sync_info(success=True, message='')
        except Exception as err:
            self.obj.update_sync_info(success=False, message=str(err))
            raise
