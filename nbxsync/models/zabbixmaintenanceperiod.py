from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from netbox.models import NetBoxModel

from nbxsync.choices import ZabbixTimePeriodDayofWeekChoices, ZabbixTimePeriodMonthChoices, ZabbixTimePeriodTypeChoices

__all__ = ('ZabbixMaintenancePeriod',)


class ZabbixMaintenancePeriod(NetBoxModel):
    zabbixmaintenance = models.ForeignKey('nbxsync.ZabbixMaintenance', on_delete=models.CASCADE, related_name='zabbixmaintenance')
    period = models.PositiveIntegerField(blank=False, validators=[MinValueValidator(300), MaxValueValidator(86399940)], help_text='Duration of the maintenance period in seconds (300-86399940)')
    timeperiod_type = models.PositiveSmallIntegerField(choices=ZabbixTimePeriodTypeChoices, default=ZabbixTimePeriodTypeChoices.ONE_TIME)
    start_date = models.DateField(blank=True, null=True)
    start_time = models.PositiveIntegerField(blank=True, validators=[MinValueValidator(0), MaxValueValidator(86400)], help_text='Time of day when the maintenance starts in seconds (0-86400)')
    every = models.PositiveIntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(12)], help_text='The recurrence of the period')
    dayofweek = ArrayField(base_field=models.PositiveSmallIntegerField(choices=ZabbixTimePeriodDayofWeekChoices), blank=True, null=True)
    day = models.PositiveIntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(31)], help_text='Day of the month when the maintenance must come into effect (1-31)')
    month = ArrayField(base_field=models.PositiveSmallIntegerField(choices=ZabbixTimePeriodMonthChoices), blank=True, null=True)

    class Meta:
        verbose_name = 'Zabbix Maintenance Period'
        verbose_name_plural = 'Zabbix Maintenance Periods'
        ordering = ('-created',)

    def clean(self):
        super().clean()
        errors = {}

        # DAILY / WEEKLY: default every=1 if missing
        if self.timeperiod_type in (ZabbixTimePeriodTypeChoices.DAILY, ZabbixTimePeriodTypeChoices.WEEKLY):
            if not self.every:
                self.every = 1

        # WEEKLY: require at least one weekday
        if self.timeperiod_type == ZabbixTimePeriodTypeChoices.WEEKLY:
            if not self.dayofweek:
                errors['dayofweek'] = "At least one day of week is required when timeperiod_type is 'weekly'."

        # MONTHLY-specific rules
        if self.timeperiod_type == ZabbixTimePeriodTypeChoices.MONTHLY:
            # month required
            if not self.month:
                errors['month'] = "Month is required when timeperiod_type is 'monthly'."

            has_dayofweek = bool(self.dayofweek)
            has_day = self.day is not None

            # Disallow both modes at once
            if has_dayofweek and has_day:
                errors['day'] = "Specify either 'day' or 'dayofweek' for monthly, not both."
                errors['dayofweek'] = "Specify either 'dayofweek' or 'day' for monthly, not both."

            if has_dayofweek:
                # every = week-of-month (1..5)
                if not self.every:
                    self.every = 1
                elif self.every not in (1, 2, 3, 4, 5):
                    errors['every'] = "For monthly periods with dayofweek, 'every' must be 1..5 (1=first, …, 5=last week)."

            else:
                # require day if no dayofweek
                if not has_day:
                    errors['day'] = "Day is required when timeperiod_type is 'monthly' and dayofweek is not set."
                if not self.every:
                    self.every = 1

        # Guard against irrelevant fields for ONE_TIME/DAILY/WEEKLY
        if self.timeperiod_type in (
            ZabbixTimePeriodTypeChoices.ONE_TIME,
            ZabbixTimePeriodTypeChoices.DAILY,
            ZabbixTimePeriodTypeChoices.WEEKLY,
        ):
            # Enforce emptiness.
            if self.timeperiod_type != ZabbixTimePeriodTypeChoices.WEEKLY and self.dayofweek:
                errors['dayofweek'] = 'dayofweek is only applicable to weekly or monthly periods.'
            if self.timeperiod_type != ZabbixTimePeriodTypeChoices.MONTHLY and (self.day is not None or self.month):
                errors['month'] = 'month is only applicable to monthly periods.'
                errors['day'] = 'day is only applicable to monthly periods.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Ensure clean() runs even on programmatic saves
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.zabbixmaintenance} ({self.timeperiod_type})'
