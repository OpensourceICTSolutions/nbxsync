from django.db import models

__all__ = ('ZabbixMaintenanceTypeChoices',)


class ZabbixMaintenanceTypeChoices(models.IntegerChoices):
    WITH_COLLECTION = 0, 'With data collection'
    WITHOUT_COLLECTION = 1, 'Without data collection'
