from nbxsync.utils.sync import run_zabbix_operation


def safe_sync(sync_class, obj, **kwargs):
    try:
        extra_args = kwargs.pop('extra_args', {})
        return run_zabbix_operation(sync_class, obj, 'sync', extra_args)
    except Exception as e:
        raise RuntimeError(f'Error syncing {sync_class.__name__}: {e}')
