from enum import Enum


class ZabbixHostStatus(str, Enum):
    ENABLED = 'enabled'
    DISABLED = 'disabled'
    DELETED = 'deleted'
    ENABLED_IN_MAINTENANCE = 'enabled_in_maintenance'
    ENABLED_NO_ALERTING = 'enabled_no_alerting'

    def __str__(self):
        return {
            'enabled': 'Enabled',
            'disabled': 'Disabled',
            'deleted': 'Deleted',
            'enabled_in_maintenance': 'Enabled, in maintenance',
            'enabled_no_alerting': 'Enabled, no alerting',
        }[self.value]
