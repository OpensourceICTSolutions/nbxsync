from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django_rq import get_queue

from nbxsync.models import ZabbixMaintenance

__all__ = ('handle_deleted_maintenance',)


@receiver(pre_delete, sender=ZabbixMaintenance)
def handle_deleted_maintenance(sender, instance, **kwargs):
    """
    Fires when a Zabbix Maintenance object is deleted.
    """

    queue = get_queue('low')
    queue.enqueue_job(
        queue.create_job(
            func='nbxsync.worker.deletemaintenance',
            args=[instance],
            timeout=9000,
        )
    )
