from nbxsync.utils.sync import ProxyGroupSync, ProxySync
from nbxsync.utils.sync.safe_sync import safe_sync

__all__ = ('SyncProxyJob',)


class SyncProxyJob:
    def __init__(self, **kwargs):
        self.instance = kwargs.get('instance')

    def run(self):
        try:
            # If part of a ProxyGroup, sync that first to ensure it exists
            if self.instance.proxygroup:
                safe_sync(ProxyGroupSync, self.instance.proxygroup)

            safe_sync(ProxySync, self.instance)
        except Exception as e:
            raise RuntimeError(f'Unexpected error: {e}')
