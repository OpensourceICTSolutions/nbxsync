from django.db import models

__all__ = ('ZabbixTimePeriodDayofWeekOptionChoices',)


class ZabbixTimePeriodDayofWeekOptionChoices(models.IntegerChoices):
    FIRST = 1, 'First'
    SECOND = 2, 'Second'
    THIRD = 3, 'Third'
    FORTH = 4, 'Forth'
    LAST = 5, 'Last'
