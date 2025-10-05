from django.db import models

__all__ = ('ZabbixMaintenanceTagOperatorChoices',)


class ZabbixMaintenanceTagOperatorChoices(models.IntegerChoices):
    EQUALS = 0, 'Equals'
    CONTAINS = 2, 'Contains'
