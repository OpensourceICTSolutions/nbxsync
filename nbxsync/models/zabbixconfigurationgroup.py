from django.db import models

from netbox.models import NetBoxModel

__all__ = ('ZabbixConfigurationGroup',)


class ZabbixConfigurationGroup(NetBoxModel):
    name = models.CharField(max_length=512, blank=False)
    description = models.CharField(max_length=1024, blank=True)

    class Meta:
        verbose_name = 'Zabbix Configuration Group'
        verbose_name_plural = 'Zabbix Configuration Groups'
        ordering = ('-created',)

    def __str__(self):
        return self.name

    def resync_all_assignments(self):
        from nbxsync.utils.cfggroup.resync_zabbixconfiggroupassignment import resync_zabbixconfigurationgroupassignment

        for assignment in self.zabbixconfigurationgroupassignment.all():
            resync_zabbixconfigurationgroupassignment(assignment)
