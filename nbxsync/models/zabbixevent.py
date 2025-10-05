from django.db import models

from netbox.models import NetBoxModel


__all__ = ('ZabbixEvent',)


class ZabbixEvent(NetBoxModel):
    zabbixserver = models.CharField(max_length=100)
    event = models.CharField(max_length=100)
    severity = models.CharField(max_length=100)
    clock = models.CharField(max_length=100)

    class Meta:
        abstract = True
