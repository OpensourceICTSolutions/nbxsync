from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django_rq import get_queue

from nbxsync.models import ZabbixServer

__all__ = ('track_changes', 'handle_postsave_server')


# We first catch the pre_save singal and detect the changed fields
@receiver(pre_save, sender=ZabbixServer)
def track_changes(sender, instance, **kwargs):
    if instance.pk:  # Only if updating (not creating new)
        old_instance = sender.objects.get(pk=instance.pk)
        changed_fields = []
        for field in instance._meta.fields:
            field_name = field.name
            old_value = getattr(old_instance, field_name)
            new_value = getattr(instance, field_name)
            if old_value != new_value:
                changed_fields.append(field_name)
        instance._changed_fields = changed_fields
    else:
        instance._changed_fields = []


# Next, we trigger on the *saved* object. This way, we can pass in the object in its saved form.
@receiver(post_save, sender=ZabbixServer)
def handle_postsave_server(sender, instance, **kwargs):
    """
    Fires when a Zabbix Server object is updated.
    """

    # We dont want to trigger on the sync fields, as these will be set on updating the templates as well
    # This causes a sync loop, something we dont want :)
    # So, if any of these fields has changed, we'll just skip this run and return early
    fields = ['last_sync', 'last_sync_state', 'last_sync_message']

    if not kwargs.get('created') and set(fields) & set(getattr(instance, '_changed_fields', [])):
        return

    queue = get_queue('low')
    queue.enqueue_job(
        queue.create_job(
            func='nbxsync.worker.synctemplates',
            args=[instance],
            timeout=9000,
        )
    )
