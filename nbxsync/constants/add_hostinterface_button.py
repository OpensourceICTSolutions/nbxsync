ADD_HOSTINTERFACE_BUTTON = """
    <a href="{% url 'plugins:nbxsync:zabbixhostinterface_add' %}?zabbixserver={{ record.zabbixserver.id }}&assigned_object_type={{ content_type.pk }}&assigned_object_id={{ object.pk }}&return_url={{ request.path }}" title="Add Zabbix Host Interface" class="btn btn-sm btn-success">
        <i class="mdi mdi-plus-thick" aria-hidden="true"></i>
    </a>
"""
