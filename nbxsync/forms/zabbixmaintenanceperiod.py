from datetime import time as _time
from django import forms
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet
from utilities.forms.widgets import DatePicker, TimePicker

from nbxsync.choices import ZabbixTimePeriodDayofWeekChoices, ZabbixTimePeriodDayofWeekOptionChoices, ZabbixTimePeriodMonthChoices, ZabbixTimePeriodMonthDateChoices, ZabbixTimePeriodTypeChoices
from nbxsync.models import ZabbixMaintenance, ZabbixMaintenancePeriod

__all__ = ('ZabbixMaintenancePeriodForm', 'ZabbixMaintenancePeriodFilterForm', 'ZabbixMaintenancePeriodBulkEditForm')


class ZabbixMaintenancePeriodForm(NetBoxModelForm):
    zabbixmaintenance = DynamicModelChoiceField(queryset=ZabbixMaintenance.objects.all(), required=True, selector=True, label=_('Maintenance'))
    days = forms.IntegerField(required=True, min_value=0, label=_('Days'))
    hours = forms.IntegerField(required=True, min_value=0, max_value=23, help_text=_('Between 0 and 23 hours'), label=_('Hours'))
    minutes = forms.IntegerField(required=True, min_value=0, max_value=59, help_text=_('Between 0 and 59 minutes'), label=_('Minutes'))
    timeperiod_type = forms.ChoiceField(label=_('Time period type'), choices=ZabbixTimePeriodTypeChoices.choices, required=True)
    start_date = forms.DateField(label=_('Start date'), widget=DatePicker(), required=False)
    start_time = forms.TimeField(label=_('Start time'), widget=TimePicker(), required=False, input_formats=['%H:%M', '%H:%M:%S'])
    every = forms.IntegerField(label=_('Every day(s)'), required=False, min_value=1, max_value=12, help_text=_('The recurrence of the period.'))

    # ArrayFields of integer choices → use TypedMultipleChoiceField to coerce to int
    dayofweek = forms.TypedMultipleChoiceField(label=_('Day(s) of week'), required=False, choices=ZabbixTimePeriodDayofWeekChoices.choices, coerce=int)
    day = forms.IntegerField(label=_('Day of month'), required=False, min_value=1, max_value=31, help_text=_('Day of the month when the maintenance must come into effect (1–31).'))
    week = forms.ChoiceField(label=_('Day of week'), required=False, choices=ZabbixTimePeriodDayofWeekOptionChoices.choices)

    month = forms.TypedMultipleChoiceField(label=_('Month(s)'), required=False, choices=ZabbixTimePeriodMonthChoices.choices, coerce=int)
    month_date = forms.ChoiceField(label=_('Date'), required=False, choices=ZabbixTimePeriodMonthDateChoices.choices)

    fieldsets = (
        FieldSet(
            'zabbixmaintenance',
            'timeperiod_type',
            'days',
            'hours',
            'minutes',
            'every',
            name=_('General'),
        ),
        FieldSet(
            'start_date',
            'start_time',
            'dayofweek',
            'day',
            'month',
            'month_date',
            name=_('Schedule'),
        ),
    )

    class Meta:
        model = ZabbixMaintenancePeriod
        fields = (
            'zabbixmaintenance',
            'timeperiod_type',
            'start_date',
            'every',
            'dayofweek',
            'day',
            'month',
            'month_date',
        )

    @staticmethod
    def _seconds_from_hms(days, hours, minutes):
        return days * 86_400 + hours * 3_600 + minutes * 60

    @staticmethod
    def _seconds_from_timeobj(t):
        if t is None:
            return None
        return t.hour * 3600 + t.minute * 60 + t.second

    def __init__(self, *args, **kwargs):
        """
        Prefill days/hours/minutes from instance.period if editing.
        """
        super().__init__(*args, **kwargs)

        instance = kwargs.get('instance') or self.instance
        if instance and instance.pk:
            total = getattr(instance, 'period', 0) or 0
            d, rem = divmod(int(total), 86_400)
            h, rem = divmod(rem, 3_600)
            m, _ = divmod(rem, 60)
            self.fields['days'].initial = d
            self.fields['hours'].initial = h
            self.fields['minutes'].initial = m

            # Prefill start_time (model stores seconds)
            if getattr(instance, 'start_time', None) is not None:
                secs = int(instance.start_time)
                hh, rem = divmod(secs, 3600)
                mm, ss = divmod(rem, 60)
                self.fields['start_time'].initial = _time(hh % 24, mm, ss)

            # Prefill dayofweek if type is Montlhy and date is Day of Week
            if instance.timeperiod_type == ZabbixTimePeriodTypeChoices.MONTHLY and bool(instance.dayofweek):
                self.fields['month_date'].initial = ZabbixTimePeriodMonthDateChoices.WEEK

            # Prefill week if type is Montlhy and date is Day of Week
            if instance.timeperiod_type == ZabbixTimePeriodTypeChoices.MONTHLY and bool(instance.every):
                self.fields['week'].initial = instance.every

        else:
            self.fields['days'].initial = 0
            self.fields['hours'].initial = 0
            self.fields['minutes'].initial = 0

    def save(self, commit=True):
        """
        Compute and set model fields derived from UI fields, then save.
        """
        obj = super().save(commit=False)

        # Compute and store period (seconds)
        days = int(self.cleaned_data.get('days') or 0)
        hours = int(self.cleaned_data.get('hours') or 0)
        minutes = int(self.cleaned_data.get('minutes') or 0)
        setattr(obj, 'period', self._seconds_from_hms(days, hours, minutes))

        # Convert TimeField -> seconds since midnight
        t = self.cleaned_data.get('start_time')  # a datetime.time or None
        obj.start_time = self._seconds_from_timeobj(t)

        if int(self.cleaned_data.get('timeperiod_type')) == ZabbixTimePeriodTypeChoices.MONTHLY and bool(self.cleaned_data.get('week', 0)):
            setattr(obj, 'every', int(self.cleaned_data.get('week') or 0))

        if commit:
            obj.save()
            self.save_m2m()
        return obj


class ZabbixMaintenancePeriodFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixMaintenancePeriod

    zabbixmaintenance = DynamicModelMultipleChoiceField(queryset=ZabbixMaintenance.objects.all(), required=False, label=_('Maintenance (name)'), to_field_name='name')
    zabbixmaintenance_id = DynamicModelMultipleChoiceField(queryset=ZabbixMaintenance.objects.all(), required=False, label=_('Maintenance (ID)'))
    timeperiod_type = forms.MultipleChoiceField(choices=ZabbixTimePeriodTypeChoices.choices, required=False, label=_('Time period type'))
    period = forms.IntegerField(required=False, label=_('Period'))
    every = forms.IntegerField(required=False, label=_('Every'))
    day = forms.IntegerField(required=False, label=_('Day of month'))
    dayofweek = forms.MultipleChoiceField(choices=ZabbixTimePeriodDayofWeekChoices.choices, required=False, label=_('Day(s) of week'))
    month = forms.MultipleChoiceField(choices=ZabbixTimePeriodMonthChoices.choices, required=False, label=_('Month(s)'))
    start_date_after = forms.DateField(required=False, label=_('Start date after'), widget=DatePicker())
    start_date_before = forms.DateField(required=False, label=_('Start date before'), widget=DatePicker())
    start_time_min = forms.IntegerField(required=False, label=_('Start time ≥ (s)'))
    start_time_max = forms.IntegerField(required=False, label=_('Start time ≤ (s)'))

    fieldsets = (
        FieldSet('q', 'filter_id', name=_('Search')),
        FieldSet('timeperiod_type', 'period', 'every', name=_('Type & Recurrence')),
        FieldSet('start_date_after', 'start_date_before', 'start_time_min', 'start_time_max', name=_('Start')),
        FieldSet('dayofweek', 'day', 'month', name=_('Calendar')),
        FieldSet('zabbixmaintenance', 'zabbixmaintenance_id', name=_('Assignment')),
    )

    tag = TagFilterField(model)


class ZabbixMaintenancePeriodBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixMaintenancePeriod

    zabbixmaintenance = DynamicModelChoiceField(queryset=ZabbixMaintenance.objects.all(), required=False, selector=True, label=_('Maintenance'))
    timeperiod_type = forms.ChoiceField(choices=ZabbixTimePeriodTypeChoices.choices, required=False, label=_('Time period type'))
    period = forms.IntegerField(label=_('Period'), required=False)
    every = forms.IntegerField(label=_('Every'), required=False, min_value=1, max_value=12)
    start_date = forms.DateField(label=_('Start date'), required=False, widget=DatePicker())
    start_time = forms.IntegerField(label=_('Start time (seconds)'), required=False, widget=TimePicker())
    dayofweek = forms.TypedMultipleChoiceField(label=_('Day(s) of week'), required=False, choices=ZabbixTimePeriodDayofWeekChoices.choices, coerce=int)
    day = forms.IntegerField(label=_('Day of month'), required=False, min_value=1, max_value=31)
    month = forms.TypedMultipleChoiceField(label=_('Month(s)'), required=False, choices=ZabbixTimePeriodMonthChoices.choices, coerce=int)

    fieldsets = (
        FieldSet(
            'zabbixmaintenance',
            'timeperiod_type',
            'period',
            'every',
            'start_date',
            'start_time',
            'dayofweek',
            'day',
            'month',
        ),
    )

    nullable_fields = (
        'period',
        'every',
        'dayofweek',
        'day',
        'month',
    )
