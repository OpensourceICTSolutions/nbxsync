def resolve_attr(obj, attr_path):
    """
    Resolve dotted attribute path, e.g. "zabbixhostgroup.groupid"
    """
    for attr in attr_path.split('.'):
        obj = getattr(obj, attr)
    return obj
