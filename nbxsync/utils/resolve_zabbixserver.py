from nbxsync.utils.resolve_attr import resolve_attr


def resolve_zabbixserver(obj, fallback_path: str = None):
    """
    Resolve the ZabbixServer from the object.
    Tries:
    1. obj.zabbixserver (default)
    2. fallback_path (e.g., "zabbixhostgroup.zabbixserver")
    """
    try:
        return getattr(obj, 'zabbixserver')
    except AttributeError:
        if fallback_path:
            try:
                return resolve_attr(obj, fallback_path)
            except AttributeError:
                return None
        return None
