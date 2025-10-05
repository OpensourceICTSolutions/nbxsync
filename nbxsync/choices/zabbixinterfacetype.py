from django.db import models

__all__ = ('ZabbixInterfaceTypeChoices',)


class ZabbixInterfaceTypeChoices(models.IntegerChoices):
    DEFAULT = 1, 'Default'
    NOTDEFAULT = 0, 'Not Default'
