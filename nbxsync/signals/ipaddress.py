from django.db import transaction
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from ipam.models import IPAddress

from nbxsync.models import ZabbixHostInterface
from nbxsync.choices import ZabbixInterfaceUseChoices

__all__ = ('track_changes', 'handle_postsave_ipaddress')


@receiver(pre_save, sender=IPAddress)
def track_changes(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_dns_name = None
        return

    instance._old_dns_name = sender.objects.filter(pk=instance.pk).values_list('dns_name', flat=True).first()


@receiver(post_save, sender=IPAddress)
def handle_postsave_ipaddress(sender, instance, created, **kwargs):
    if created:
        return

    old = getattr(instance, '_old_dns_name', None)
    new = instance.dns_name

    if old == new:
        return

    def do_update():
        ZabbixHostInterface.objects.filter(ip=instance.id, useip=ZabbixInterfaceUseChoices.DNS, zabbixconfigurationgroup__isnull=False).update(dns=new)

    transaction.on_commit(do_update)
