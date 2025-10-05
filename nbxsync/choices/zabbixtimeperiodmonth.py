from django.db import models

__all__ = ('ZabbixTimePeriodMonthChoices',)


class ZabbixTimePeriodMonthChoices(models.IntegerChoices):
    JANUARY = 1, 'January'
    FEBRUARY = 2, 'February'
    MARCH = 4, 'March'
    APRIL = 8, 'April'
    MAY = 16, 'May'
    JUNE = 32, 'June'
    JULI = 64, 'Juli'
    AUGUST = 128, 'August'
    SEPTEMBER = 256, 'Septembet'
    OCTOBER = 512, 'October'
    NOVEMBER = 1024, 'November'
    DECEMBER = 2048, 'December'
