from nbxsync.utils.sync import run_zabbix_operation


def safe_delete(sync_class, obj, **kwargs):
    try:
        extra_args = kwargs.pop('extra_args', {})
        return run_zabbix_operation(sync_class, obj, 'delete', extra_args)
    except Exception as e:
        raise RuntimeError(f'Error deleting {sync_class.__name__}: {e}')
