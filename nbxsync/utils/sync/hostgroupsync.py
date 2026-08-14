import logging

from .syncbase import ZabbixSyncBase
from nbxsync.models import ZabbixHostgroup

logger = logging.getLogger(__name__)


def ensure_parent_hostgroups(api, name):
    """Materialize missing parent groups of a nested name, parent-first.

    Zabbix treats nesting as a name convention: creating 'A/B/C' does not
    auto-create 'A' and 'A/B' — they stay phantom groups that can never
    hold hosts or permissions. Because Zabbix only inherits user-group
    permissions and tag filters into a subgroup when its parent already
    exists, parents must be created before their children.

    Idempotent: existing parents are found by exact name and left alone.
    Malformed names (empty segments, leading/trailing slashes) are skipped;
    the Zabbix API rejects them on the leaf create either way."""
    if '//' in name or name != name.strip('/'):
        return
    segments = name.split('/')
    for depth in range(1, len(segments)):
        parent = '/'.join(segments[:depth])
        if api.hostgroup.get(filter={'name': parent}):
            continue
        result = api.hostgroup.create({'name': parent})
        logger.info("Created parent hostgroup '%s' (groupid=%s)", parent, result['groupids'][0])


class HostGroupSync(ZabbixSyncBase):
    id_field = 'zabbixhostgroup.groupid'
    sot_key = 'hostgroup'
    zabbixserver_path = 'zabbixhostgroup.zabbixserver'

    def get_name_value(self):
        name, _state = self.obj.render()
        if not _state and self.obj.is_template():
            return None
        return name

    def try_create(self):
        # For template-based assignments that can't render against the
        # assigned object (e.g. {{ object.role.name }} on a DeviceRole),
        # skip creation — the group is created on-demand during host sync.
        name, state = self.obj.render()
        if not state and self.obj.is_template():
            return None
        self._ensure_parent_groups(name)
        return super().try_create()

    def _ensure_parent_groups(self, name):
        """Create missing parents for nested group names before the leaf.

        Zabbix inherits user-group permissions and tag filters into a subgroup
        only when its parent already exists — see ensure_parent_hostgroups()."""
        ensure_parent_hostgroups(self.api, name)

    def api_object(self):
        return self.api.hostgroup

    def get_create_params(self):
        name, _state = self.obj.render()
        if not _state and self.obj.is_template():
            return {}
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
            return

        # print('HostGroupSync: Detected template value, skipping groupid update.')
        # Get Hostgroup by ZabbixServer and ID
        # If not, create it
        hostgroup = ZabbixHostgroup.objects.filter(zabbixserver=self.obj.zabbixhostgroup.zabbixserver, groupid=value).first()
        if hostgroup:
            hostgroup.groupid = value
            hostgroup.save()
            return

        name, _state = self.obj.render()
        if not _state and self.obj.is_template():
            return  # Cannot render template against assignment object

        zabbixserver = self.obj.zabbixhostgroup.zabbixserver
        # Try to find an existing local representation for the rendered Zabbix group.
        # Dynamic groups created from templates are stored with the rendered group
        # name in both `name` and `value`, so check either field without raising.
        hostgroup = ZabbixHostgroup.objects.filter(zabbixserver=zabbixserver, name=name).first() or ZabbixHostgroup.objects.filter(zabbixserver=zabbixserver, value=name).first()

        if hostgroup:
            hostgroup.groupid = value
            hostgroup.save()
            return

        # Not found by name, so create it
        ZabbixHostgroup(zabbixserver=zabbixserver, name=name, value=name, groupid=value, description='Automatically generated from template').save()

    def get_id(self):
        if self.obj.is_template():
            # print('HostGroupSync: Detected template value, skipping groupid usage.')
            return None
        return super().get_id()
