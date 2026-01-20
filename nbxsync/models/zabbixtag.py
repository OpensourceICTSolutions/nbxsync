import re

from django.db import models
from netbox.models import NetBoxModel

__all__ = ('ZabbixTag',)

TEMPLATE_PATTERN = re.compile(r'({{.*?}}|{%-?\s*.*?\s*-?%}|{#.*?#})')


class ZabbixTag(NetBoxModel):
    name = models.CharField(max_length=512, blank=False)
    description = models.CharField(max_length=512, blank=True)
    tag = models.CharField(max_length=255, blank=False)
    value = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Zabbix Tag'
        verbose_name_plural = 'Zabbix Tags'
        ordering = ('-created',)

    def is_template(self):
        return bool(TEMPLATE_PATTERN.search(self.value))

    def __str__(self):
        return f'{self.name} ({self.tag})'
