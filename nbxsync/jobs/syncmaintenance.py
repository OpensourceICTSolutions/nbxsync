from nbxsync.utils.sync import MaintenanceSync
from nbxsync.utils.sync.safe_sync import safe_sync

__all__ = ('SyncMaintenceJob',)


class SyncMaintenceJob:
    def __init__(self, **kwargs):
        self.instance = kwargs.get('instance')

    def run(self):
        if not self.zabbixserver.sync_enabled:
            return

        try:
            safe_sync(MaintenanceSync, self.instance)
        except Exception as e:
            raise RuntimeError(f'Unexpected error: {e}')
