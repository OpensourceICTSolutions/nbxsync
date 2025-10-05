from django_rq import get_queue

from netbox.jobs import JobRunner, system_job

from nbxsync.models import ZabbixServer
from nbxsync.settings import get_plugin_settings


def GetSyncInterval():
    pluginsettings = get_plugin_settings()
    return pluginsettings.backgroundsync.templates.interval


@system_job(interval=GetSyncInterval())
class SyncTemplatesJob(JobRunner):
    class Meta:
        name = 'Zabbix Sync Templates job'

    def run(self, *args, **kwargs):
        for zabbixserver in ZabbixServer.objects.all():
            queue = get_queue('low')
            queue.enqueue_job(
                queue.create_job(
                    func='nbxsync.worker.synctemplates',
                    args=[zabbixserver],
                    timeout=9000,
                )
            )
