from django.db import models

__all__ = ('ZabbixTimePeriodTypeChoices',)


class ZabbixTimePeriodTypeChoices(models.IntegerChoices):
    ONE_TIME = 0, 'One time only'
    DAILY = 2, 'Daily'
    WEEKLY = 3, 'Weekly'
    MONTHLY = 4, 'Monthly'
