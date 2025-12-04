from django.contrib.contenttypes.models import ContentType

from nbxsync.choices.zabbixstatus import ZabbixHostStatus
from nbxsync.models import ZabbixServerAssignment
from nbxsync.settings import get_plugin_settings
from nbxsync.utils import get_assigned_zabbixobjects
from nbxsync.utils.sync import HostGroupSync, HostInterfaceSync, HostSync, ProxyGroupSync, ProxySync, run_zabbix_operation
from nbxsync.utils.sync.safe_delete import safe_delete
from nbxsync.utils.sync.safe_sync import safe_sync

__all__ = ('SyncHostJob',)


class SyncHostJob:
    def __init__(self, **kwargs):
        self.instance = kwargs.get('instance')  # This is the Device or VirtualMachine object

    def run(self):
        object_ct = ContentType.objects.get_for_model(self.instance)

        zabbixserver_assignments = ZabbixServerAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=self.instance.pk)

        status = self.instance.status
        object_type = self.instance._meta.model_name  # "device" or "virtualmachine"
        pluginsettings = get_plugin_settings()
        status_mapping = getattr(pluginsettings.statusmapping, object_type, {})
        zabbix_status = status_mapping.get(status)

        for assignment in zabbixserver_assignments:
            if zabbix_status == ZabbixHostStatus.DELETED:
                self.delete_host(assignment)
            else:
                self.sync_host(assignment)
                self.verify_hostinterfaces(assignment)
                # Check if host has Maintenance, if so: sync Maintenance

    def delete_host(self, assignment):
        safe_delete(HostSync, assignment)

    def verify_hostinterfaces(self, assignment):
        all_objects = get_assigned_zabbixobjects(self.instance)
        run_zabbix_operation(HostSync, assignment, 'verify_hostinterfaces', extra_args={'all_objects': all_objects})

    def sync_host(self, assignment):
        try:
            all_objects = get_assigned_zabbixobjects(self.instance)
            # Add the assigned_objects attribute, so we dont have to do this expensive calculation again later on :)
            assignment.assigned_objects = all_objects

            # Create all hostgroups
            for hostgroup in all_objects['hostgroups']:
                safe_sync(HostGroupSync, hostgroup)

            # Sync ProxyGroups and proxies (in that order!)
            # If the ZabbixServer Assignment has a Proxy, sync it
            if assignment.zabbixproxy:
                # If the ZabbixProxy is assigned to a ProxyGroup, sync the group first.
                if assignment.zabbixproxy.proxygroup:
                    safe_sync(ProxyGroupSync, assignment.zabbixproxy.proxygroup)
                safe_sync(ProxySync, assignment.zabbixproxy)

            # If the ZabbixServer Assignment has a ProxyGroup, sync it
            if assignment.zabbixproxygroup:
                safe_sync(ProxyGroupSync, assignment.zabbixproxygroup)

            # Sync the actual Host
            try:
                safe_sync(HostSync, assignment, extra_args={'all_objects': all_objects})
            except Exception as e:
                # This can happen, in cases where the host exists, a new HostInterface is added (SNMP for example) and a new template (which requires SNMP)
                # In such cases, the Host Update will fail, due to the Interface not existing yet.
                # Fail silently, so we can create the interface - and we'll sync the template on the next run...
                pass

            # Once the Host exists and we have a HostId, time to sync the interfaces
            for hostinterface in all_objects['hostinterfaces']:
                safe_sync(HostInterfaceSync, hostinterface, extra_args={'hostid': assignment.hostid})

            safe_sync(HostSync, assignment, extra_args={'all_objects': all_objects})

        except Exception as e:
            raise RuntimeError(f'Unexpected error: {e}')
