from django.db import models

__all__ = ('ZabbixTimePeriodMonthDateChoices',)


class ZabbixTimePeriodMonthDateChoices(models.IntegerChoices):
    MONTH = 1, 'Day of Month'
    WEEK = 2, 'Day of Week'
