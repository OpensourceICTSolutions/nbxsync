from django.db import models

__all__ = ('ZabbixInterfaceUseChoices',)


class ZabbixInterfaceUseChoices(models.IntegerChoices):
    DNS = 0, 'DNS'
    IP = 1, 'IP'
