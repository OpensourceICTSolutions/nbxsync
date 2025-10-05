from django.db import models

__all__ = ('ZabbixHostInventoryModeChoices',)


class ZabbixHostInventoryModeChoices(models.IntegerChoices):
    DISABLED = -1, 'Disabled'
    MANUAL = 0, 'Manual'
    AUTOMATIC = 1, 'Automatic'
