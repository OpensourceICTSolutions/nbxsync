from django.db import models

from netbox.models import NetBoxModel


__all__ = ('ZabbixProblem',)


class ZabbixProblem(NetBoxModel):
    zabbixserver = models.CharField(max_length=100)
    problem = models.CharField(max_length=100)
    severity = models.CharField(max_length=100)
    clock = models.CharField(max_length=100)

    class Meta:
        abstract = True
