from django.db import models

__all__ = ('ZabbixProxyTypeChoices',)


class ZabbixProxyTypeChoices(models.IntegerChoices):
    ACTIVE = 0, 'Active'
    PASSIVE = 1, 'Passive'
