from django_rq import get_queue

from netbox.jobs import JobRunner, system_job

from nbxsync.models import ZabbixServer, ZabbixProxy
from nbxsync.settings import get_plugin_settings


def GetSyncInterval():
    pluginsettings = get_plugin_settings()
    return pluginsettings.backgroundsync.proxies.interval


@system_job(interval=GetSyncInterval())
class SyncProxiesJob(JobRunner):
    class Meta:
        name = 'Zabbix Sync Proxies job'

    def run(self, *args, **kwargs):
        for zabbixserver in ZabbixServer.objects.all():
            for proxy in ZabbixProxy.objects.filter(zabbixserver=zabbixserver):
                queue = get_queue('low')
                queue.enqueue_job(
                    queue.create_job(
                        func='nbxsync.worker.syncproxy',
                        args=[proxy],
                        timeout=9000,
                    )
                )
