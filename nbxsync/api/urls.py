from netbox.api.routers import NetBoxRouter

from nbxsync.api.views import (
    ZabbixServerViewSet,
    ZabbixServerAssignmentViewSet,
    ZabbixTemplateViewSet,
    ZabbixTemplateAssignmentViewSet,
    ZabbixMacroViewSet,
    ZabbixMacroAssignmentViewSet,
    ZabbixMacroAssignmentViewSet,
    ZabbixTagViewSet,
    ZabbixTagAssignmentViewSet,
    ZabbixHostInterfaceViewSet,
    ZabbixProxyGroupViewSet,
    ZabbixProxyViewSet,
    ZabbixHostgroupViewSet,
    ZabbixHostgroupAssignmentViewSet,
    ZabbixHostgroupAssignmentViewSet,
    ZabbixHostInventoryViewSet,
    ZabbixMaintenanceViewSet,
    ZabbixMaintenancePeriodViewSet,
    ZabbixMaintenanceObjectAssignmentViewSet,
    ZabbixMaintenanceTagAssignmentViewSet,
    ZabbixConfigurationGroupViewSet,
    ZabbixConfigurationGroupAssignmentViewSet,
)


router = NetBoxRouter()
router.register('zabbixserver', ZabbixServerViewSet)
router.register('zabbixserverassignment', ZabbixServerAssignmentViewSet)
router.register('zabbixtemplate', ZabbixTemplateViewSet)
router.register('zabbixtemplateassignment', ZabbixTemplateAssignmentViewSet)
router.register('zabbixmacro', ZabbixMacroViewSet)
router.register('zabbixmacroassignment', ZabbixMacroAssignmentViewSet)
router.register('zabbixtag', ZabbixTagViewSet)
router.register('zabbixtagassignment', ZabbixTagAssignmentViewSet)
router.register('zabbixhostinterface', ZabbixHostInterfaceViewSet)
router.register('zabbixproxygroup', ZabbixProxyGroupViewSet)
router.register('zabbixproxy', ZabbixProxyViewSet)
router.register('zabbixhostgroup', ZabbixHostgroupViewSet)
router.register('zabbixhostgroupassignment', ZabbixHostgroupAssignmentViewSet)
router.register('zabbixhostinventory', ZabbixHostInventoryViewSet)
router.register('zabbixmaintenance', ZabbixMaintenanceViewSet)
router.register('zabbixmaintenanceperiod', ZabbixMaintenancePeriodViewSet)
router.register('zabbixmaintenanceobjectassignment', ZabbixMaintenanceObjectAssignmentViewSet)
router.register('zabbixmaintenancetagassignment', ZabbixMaintenanceTagAssignmentViewSet)
router.register('zabbixconfigurationgroup', ZabbixConfigurationGroupViewSet)
router.register('zabbixconfigurationgroupassignment', ZabbixConfigurationGroupAssignmentViewSet)

urlpatterns = router.urls
