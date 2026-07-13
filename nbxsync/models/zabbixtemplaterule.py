import re

from django.core.exceptions import ValidationError
from django.db import models

from netbox.models import NetBoxModel

__all__ = ('ZabbixTemplateRule',)


class ZabbixTemplateRule(NetBoxModel):
    name = models.CharField(max_length=100, blank=False)
    description = models.CharField(max_length=200, blank=True)
    pattern = models.CharField(max_length=500, blank=False, help_text='Regex pattern matched against Platform name')
    zabbixtemplate = models.ForeignKey(to='nbxsync.ZabbixTemplate', on_delete=models.CASCADE, related_name='zabbixtemplaterules')
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=100, help_text='Lower value = higher priority')

    class Meta:
        verbose_name = 'Zabbix Template Rule'
        verbose_name_plural = 'Zabbix Template Rules'
        ordering = ('priority', 'name')

    def clean(self):
        super().clean()
        try:
            re.compile(self.pattern)
        except re.error as e:
            raise ValidationError({'pattern': f'Invalid regex: {e}'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def matches(self, platform_name):
        if not platform_name or not self.enabled:
            return False
        return bool(re.search(self.pattern, platform_name, re.IGNORECASE))

    def __str__(self):
        return f'{self.name} ({self.pattern})'
