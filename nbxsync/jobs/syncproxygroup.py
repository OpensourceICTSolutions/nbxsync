from nbxsync.utils.sync import ProxyGroupSync
from nbxsync.utils.sync.safe_sync import safe_sync

__all__ = ('SyncProxyGroupJob',)


class SyncProxyGroupJob:
    def __init__(self, **kwargs):
        self.instance = kwargs.get('instance')

    def run(self):
        try:
            safe_sync(ProxyGroupSync, self.instance)
        except Exception as e:
            raise RuntimeError(f'Unexpected error: {e}')
