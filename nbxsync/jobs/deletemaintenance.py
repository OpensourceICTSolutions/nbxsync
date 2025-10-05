from nbxsync.utils.sync import MaintenanceSync
from nbxsync.utils.sync.safe_delete import safe_delete

__all__ = ('DeleteMaintenanceJob',)


class DeleteMaintenanceJob:
    def __init__(self, **kwargs):
        self.instance = kwargs.get('instance')  # This is the Zabbix Maintenance object

    def run(self):
        safe_delete(MaintenanceSync, self.instance)
