from rest_framework import serializers

from netbox.api.fields import ChoiceField
from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.models import ZabbixMaintenancePeriod

__all__ = ('ZabbixMaintenancePeriodSerializer',)


class ZabbixMaintenancePeriodSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixmaintenanceperiod-detail')
    timeperiod_type = ChoiceField(choices=ZabbixMaintenancePeriod._meta.get_field('timeperiod_type').choices)
    timeperiod_type_display = serializers.CharField(source='get_timeperiod_type_display', read_only=True)
    dayofweek = serializers.ListField(child=serializers.IntegerField(), allow_null=True, required=False)
    month = serializers.ListField(child=serializers.IntegerField(), allow_null=True, required=False)
    dayofweek_display = serializers.SerializerMethodField(read_only=True)
    month_display = serializers.SerializerMethodField(read_only=True)
    start_time_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ZabbixMaintenancePeriod
        fields = (
            'url',
            'id',
            'display',
            'zabbixmaintenance',
            'period',
            'timeperiod_type',
            'timeperiod_type_display',
            'start_date',
            'start_time',
            'start_time_display',
            'every',
            'dayofweek',
            'dayofweek_display',
            'day',
            'month',
            'month_display',
            'created',
            'last_updated',
        )
        brief_fields = ('url', 'id', 'display')

    #
    # Display helpers
    #
    def get_dayofweek_display(self, obj):
        return self._choices_array_display(obj, 'dayofweek')

    def get_month_display(self, obj):
        return self._choices_array_display(obj, 'month')

    def _choices_array_display(self, obj, field_name):
        values = getattr(obj, field_name, None) or []
        field = obj._meta.get_field(field_name)
        choices = dict(getattr(field.base_field, 'choices', ()) or ())
        return [choices.get(v, v) for v in values]

    def get_start_time_display(self, obj):
        if obj.start_time is None:
            return None
        seconds = int(obj.start_time)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f'{h:02d}:{m:02d}'
