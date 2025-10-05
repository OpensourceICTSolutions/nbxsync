from django.contrib.postgres.fields import ArrayField
from django.db import models

from netbox.models import NetBoxModel

from nbxsync.choices import HostInterfaceRequirementChoices

__all__ = ('ZabbixTemplate',)


def default_interfacerequirement():
    return [HostInterfaceRequirementChoices.NONE.value]


class ZabbixTemplate(NetBoxModel):
    name = models.CharField(max_length=512, blank=False)
    templateid = models.IntegerField(blank=False)
    zabbixserver = models.ForeignKey('nbxsync.ZabbixServer', on_delete=models.CASCADE, related_name='templates')
    interface_requirements = ArrayField(base_field=models.IntegerField(choices=HostInterfaceRequirementChoices.choices), default=default_interfacerequirement, help_text='Host interface types required for this template. Values: AGENT, SNMP, IPMI, JMX, ANY, NONE')
    prerequisite_models = ('nbxsync.ZabbixServer',)

    class Meta:
        verbose_name = 'Zabbix Template'
        verbose_name_plural = 'Zabbix Templates'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=['name', 'zabbixserver'],
                name='%(app_label)s_%(class)s_unique__name_per_server',
                violation_error_message='Template name must be unique per Zabbix Server',
            ),
            models.UniqueConstraint(
                fields=['templateid', 'zabbixserver'],
                name='%(app_label)s_%(class)s_unique__templateid_per_server',
                violation_error_message='Template ID must be unique per Zabbix Server',
            ),
        ]

    def get_interface_requirements_display(self):
        return [HostInterfaceRequirementChoices(value).label for value in self.interface_requirements]

    def __str__(self):
        return f'{self.name} ({self.zabbixserver.name})'
