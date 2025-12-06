from django_rq import get_queue

from netbox.jobs import JobRunner, system_job

from nbxsync.models import ZabbixServer, ZabbixMaintenance
from nbxsync.settings import get_plugin_settings
from nbxsync.utils import get_maintenance_can_sync


def GetSyncInterval():
    pluginsettings = get_plugin_settings()
    return pluginsettings.backgroundsync.maintenance.interval


@system_job(interval=GetSyncInterval())
class SyncMaintenanceJob(JobRunner):
    class Meta:
        name = 'Zabbix Sync Maintenance job'

    def run(self, *args, **kwargs):
        for zabbixserver in ZabbixServer.objects.all():
            for mw in ZabbixMaintenance.objects.filter(zabbixserver=zabbixserver):
                if not get_maintenance_can_sync(mw):
                    continue

                queue = get_queue('low')
                queue.enqueue_job(
                    queue.create_job(
                        func='nbxsync.worker.syncmaintenance',
                        args=[mw],
                        timeout=9000,
                    )
                )
