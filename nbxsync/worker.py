import logging

from django_rq import job
from nbxsync.jobs import *

logger = logging.getLogger('worker')


@job('low')
def synchost(instance):
    worker = SyncHostJob(instance=instance)
    worker.run()


@job('low')
def deletehost(instance):
    worker = DeleteHostJob(instance=instance)
    worker.run()


@job('low')
def syncproxygroup(instance):
    worker = SyncProxyGroupJob(instance=instance)
    worker.run()


@job('low')
def syncproxy(instance):
    worker = SyncProxyJob(instance=instance)
    worker.run()


@job('low')
def synctemplates(instance):
    worker = SyncTemplatesJob(instance=instance)
    worker.run()


@job('low')
def syncmaintenance(instance):
    worker = SyncMaintenceJob(instance=instance)
    worker.run()


@job('low')
def deletemaintenance(instance):
    worker = DeleteMaintenanceJob(instance=instance)
    worker.run()
