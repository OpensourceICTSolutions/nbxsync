from django_rq import get_queue

from netbox.jobs import JobRunner, system_job

from nbxsync.models import ZabbixServerAssignment, ZabbixConfigurationGroup
from nbxsync.settings import get_plugin_settings


def GetSyncInterval():
    pluginsettings = get_plugin_settings()
    return pluginsettings.backgroundsync.objects.interval


@system_job(interval=GetSyncInterval())
class SyncObjectsJob(JobRunner):
    class Meta:
        name = 'Zabbix Sync Hosts job'

    def run(self, *args, **kwargs):
        synced_objects = []
        for obj in ZabbixServerAssignment.objects.all():
            # dont try to sync ZabbixConfigurationGroups
            if isinstance(obj.assigned_object, ZabbixConfigurationGroup):
                continue

            if obj.assigned_object in synced_objects:
                return
            else:
                synced_objects.append(obj.assigned_object)

            instance = obj.assigned_object
            queue = get_queue('low')
            queue.enqueue_job(
                queue.create_job(
                    func='nbxsync.worker.synchost',
                    args=[instance],
                    timeout=9000,
                )
            )
