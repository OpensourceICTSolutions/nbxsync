from django.core.exceptions import ValidationError
from django.db import models

from netbox.models import NetBoxModel

from nbxsync.models import SyncInfoModel


__all__ = ('ZabbixProxyGroup',)


class ZabbixProxyGroup(SyncInfoModel, NetBoxModel):
    zabbixserver = models.ForeignKey('nbxsync.ZabbixServer', on_delete=models.CASCADE, related_name='zabbixproxygroups')
    proxy_groupid = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    failover_delay = models.CharField(max_length=10, default='1m', help_text='e.g., 30s, 1m; must be between 10s and 15m')
    min_online = models.PositiveIntegerField(default=1, help_text='Minimum number of online proxies (1–1000)')

    prerequisite_models = ('nbxsync.ZabbixServer',)

    class Meta:
        verbose_name = 'Zabbix Proxy Group'
        verbose_name_plural = 'Zabbix Proxy Groups'
        ordering = ('-created',)

    def __str__(self):
        return self.name

    def clean(self):
        errors = {}

        # Validate failover_delay format and bounds (10s–15m)
        if not isinstance(self.failover_delay, str):
            errors['failover_delay'] = "Failover delay must be a string like '30s', '1m'."
        else:
            import re

            match = re.fullmatch(r'(\d+)([sm])', self.failover_delay)
            if not match:
                errors['failover_delay'] = "Invalid format—use integer + 's' or 'm', e.g. '90s', '5m'."
            else:
                val, unit = int(match.group(1)), match.group(2)
                seconds = val * (60 if unit == 'm' else 1)
                if seconds < 10 or seconds > 900:
                    errors['failover_delay'] = 'Value must be between 10s and 15m.'

        # Check min_online bounds
        if self.min_online < 1 or self.min_online > 1000:
            errors['min_online'] = 'min_online must be between 1 and 1000.'

        if errors:
            raise ValidationError(errors)
