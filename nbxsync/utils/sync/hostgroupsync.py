from .syncbase import ZabbixSyncBase
from nbxsync.models import ZabbixHostgroup


class HostGroupSync(ZabbixSyncBase):
    id_field = 'zabbixhostgroup.groupid'
    sot_key = 'hostgroup'
    zabbixserver_path = 'zabbixhostgroup.zabbixserver'

    def get_name_value(self):
        name, _state = self.obj.render()
        return name

    def api_object(self):
        return self.api.hostgroup

    def get_create_params(self):
        name, _state = self.obj.render()
        return {
            'name': name,
        }

    def get_update_params(self, **kwargs):
        params = self.get_create_params()
        object_id = kwargs.get('object_id')
        if object_id is None:
            object_id = self.get_id()  # falls back to stored groupid (for non-template)
        params['groupid'] = object_id
        return params

    def result_key(self):
        return 'groupids'

    # -- Override set_id() and get_id() --
    # WHY:
    # Zabbix requires hostgroup names to be globally unique. In this plugin,
    # ZabbixHostgroupAssignment.value can be a Jinja2 template that renders
    # a dynamic group name per assigned object (e.g., per device or site).
    #
    # When using a static value, we store the groupid on the shared
    # ZabbixHostgroup object and reuse it. However, when the value is dynamic,
    # each rendered result is logically a separate Zabbix group — even if the
    # same ZabbixHostgroup is referenced. In this case, saving or using the
    # shared groupid would be incorrect and could cause name conflicts in Zabbix.
    #
    # HOW:
    # If the assignment value is a Jinja2 template (i.e., dynamic),
    # we override get_id() to return None — forcing the sync logic
    # to fall back to find_by_name(), ensuring proper name-based matching.
    # We also skip setting the groupid for dynamic values in set_id().

    def set_id(self, value):
        if not self.obj.is_template():
            super().set_id(value)
        else:
            # print('HostGroupSync: Detected template value, skipping groupid update.')
            # Get Hostgroup by ZabbixServer and ID
            # If not, create it
            hostgroup = ZabbixHostgroup.objects.filter(zabbixserver=self.obj.zabbixhostgroup.zabbixserver, groupid=value).first()
            if hostgroup:
                hostgroup.groupid = value
                hostgroup.save()
            else:
                name, _state = self.obj.render()
                ZabbixHostgroup(zabbixserver=self.obj.zabbixhostgroup.zabbixserver, name=name, value=name, groupid=value, description='Automatically generated from template').save()

    def get_id(self):
        if self.obj.is_template():
            # print('HostGroupSync: Detected template value, skipping groupid usage.')
            return None
        return super().get_id()
