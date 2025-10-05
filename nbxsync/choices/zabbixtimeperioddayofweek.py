from django.db import models

__all__ = ('ZabbixTimePeriodDayofWeekChoices',)


class ZabbixTimePeriodDayofWeekChoices(models.IntegerChoices):
    MONDAY = 1, 'Monday'
    TUESDAY = 2, 'Tuesday'
    WEDNESDAY = 4, 'Wednesday'
    THURSDAY = 8, 'Thursday'
    FRIDAY = 16, 'Friday'
    SATURDAY = 32, 'Saturday'
    SUNDAY = 64, 'Sunday'
