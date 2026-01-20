import re

from django.db import models

from netbox.models import NetBoxModel

__all__ = ('ZabbixHostgroup',)

TEMPLATE_PATTERN = re.compile(r'({{.*?}}|{%-?\s*.*?\s*-?%}|{#.*?#})')


class ZabbixHostgroup(NetBoxModel):
    zabbixserver = models.ForeignKey('nbxsync.ZabbixServer', on_delete=models.CASCADE, related_name='zabbixserver')
    name = models.CharField(max_length=512, blank=False)
    groupid = models.IntegerField(blank=True, null=True)

    description = models.CharField(max_length=512, blank=True)
    value = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Zabbix Hostgroup'
        verbose_name_plural = 'Zabbix Hostgroups'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=['name', 'zabbixserver'],
                name='%(app_label)s_%(class)s_unique__hostgroup_per_zabbixserver',
                violation_error_message='Hostgroup must be unique per Zabbix Server',
            ),
            models.UniqueConstraint(
                fields=['groupid', 'zabbixserver'],
                name='%(app_label)s_%(class)s_unique__hostgroupid_per_zabbixserver',
                violation_error_message='Hostgroup ID must be unique per Zabbix Server',
            ),
        ]

    def is_template(self):
        return bool(TEMPLATE_PATTERN.search(self.value))

    def __str__(self):
        return f'{self.name} ({self.zabbixserver.name})'
