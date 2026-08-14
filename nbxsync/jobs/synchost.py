import copy
import logging

from django.contrib.contenttypes.models import ContentType

from nbxsync.choices.zabbixstatus import ZabbixHostStatus
from nbxsync.settings import get_plugin_settings
from nbxsync.utils import get_assigned_zabbixobjects
from nbxsync.utils.host_binding import HostBindingDeleteProxy, get_managed_host_id, iter_host_bindings
from nbxsync.utils.sync import HostGroupSync, HostInterfaceSync, HostSync, ProxyGroupSync, ProxySync, run_zabbix_operation
from nbxsync.utils.sync.safe_delete import safe_delete
from nbxsync.utils.sync.safe_sync import safe_sync
from nbxsync.utils.trigger_dependency_sync import sync_device_trigger_dependencies

logger = logging.getLogger(__name__)

__all__ = ('SyncHostJob',)


class SyncHostJob:
    def __init__(self, **kwargs):
        self.instance = kwargs.get('instance')  # This is the Device or VirtualMachine object
        self.partial_errors = []

    def _prepare_assignment(self, assignment):
        """
        If the assignment is inherited (not directly on this device/VM),
        create a detached copy so that hostid and sync metadata cannot be
        persisted back to the Site-level (or Platform-level) assignment row.

        Uses pk=None (Django idiom for "new object") so any accidental save()
        would INSERT rather than UPDATE the original row.  The _is_inherited_copy
        flag is checked by SyncBase.sync() to skip save() entirely.
        """
        instance_ct = ContentType.objects.get_for_model(self.instance)
        is_direct = assignment.assigned_object_type_id == instance_ct.id and assignment.assigned_object_id == self.instance.pk
        if not is_direct:
            assignment = copy.copy(assignment)
            assignment.pk = None
            assignment._is_inherited_copy = True
        return assignment

    def _is_excluded(self, pluginsettings, all_objects):
        """Check whether this device/VM should be excluded from Zabbix sync.

        When a ZabbixTag with the configured ``exclude_tag`` name (default:
        empty string — disabled) is assigned to a DeviceRole, Platform, Site,
        Manufacturer, ConfigGroup, or directly to the Device/VM, every host
        that inherits from that object is excluded. The tag is never pushed
        to Zabbix — it is only used as a signal during sync resolution.

        Returns True if the host should be excluded.
        """
        exclude_tag = getattr(pluginsettings, 'exclude_tag', '')
        if not exclude_tag:
            return False

        for tag_assignment in all_objects.get('tags', []):
            if tag_assignment.zabbixtag.tag == exclude_tag:
                logger.debug('Excluding %s: exclude tag "%s" present', self.instance, exclude_tag)
                return True

        return False

    def run(self):
        # Recoverable per-host errors are collected so that independent work
        # (other interfaces, other Zabbix servers, binding retirement) still
        # runs, while the job as a whole still reports the failure.
        self.partial_errors = []

        all_objects = get_assigned_zabbixobjects(self.instance)
        zabbixserver_assignments = all_objects.get('server_assignments', [])

        status = self.instance.status
        object_type = self.instance._meta.model_name  # "device" or "virtualmachine"
        pluginsettings = get_plugin_settings()
        status_mapping = getattr(pluginsettings.statusmapping, object_type, {})
        zabbix_status = status_mapping.get(status)

        assigned_server_ids = {assignment.zabbixserver_id for assignment in zabbixserver_assignments}

        # Excluded objects must retire every active binding instead of merely
        # skipping future synchronization.
        if self._is_excluded(pluginsettings, all_objects):
            for assignment in zabbixserver_assignments:
                if assignment.sync_enabled and assignment.zabbixserver.sync_enabled:
                    assignment = self._prepare_assignment(assignment)
                    # Exclusion is an explicit operator decision, so it deletes
                    # unconditionally — unlike lost server assignments, which are
                    # gated on allow_inherited_deletion (see _retire_unassigned_bindings).
                    self.delete_host(assignment)
            self._retire_unassigned_bindings(assigned_server_ids)
            logger.info('Skipping sync for %s (excluded)', self.instance)
            self._raise_on_partial_failure()
            return
        for assignment in zabbixserver_assignments:
            assigned_server_ids.add(assignment.zabbixserver_id)

            if not assignment.sync_enabled or not assignment.zabbixserver.sync_enabled:
                continue

            # Detach inherited assignments so hostid/sync-info is not written
            # back to the source row (e.g. a Site-level assignment).
            assignment = self._prepare_assignment(assignment)

            if zabbix_status == ZabbixHostStatus.DELETED:
                self.delete_host(assignment)
            else:
                self.check_default_hostinterface(assignment)
                self.sync_host(assignment)
                self.verify_hostinterfaces(assignment)

        # Retire any durable bindings whose server assignment has disappeared.
        # (This covers loss of all assignments, including inherited ones.)
        self._retire_unassigned_bindings(assigned_server_ids)

        trigger_config = getattr(pluginsettings, 'trigger_dependencies', None)
        if object_type == 'device' and zabbix_status != ZabbixHostStatus.DELETED and trigger_config is not None and trigger_config.enabled:
            try:
                sync_device_trigger_dependencies(self.instance)
            except Exception:
                logger.exception('Trigger dependency sync failed for %s; continuing.', self.instance)

        self._raise_on_partial_failure()

    def _deletion_blocked(self, reason, zabbixserver, hostid):
        """Report whether an inheritance-driven deletion may proceed.

        Deleting a Zabbix host discards its measurement history, and the
        trigger can be as indirect as moving a Site into another SiteGroup. When
        ``allow_inherited_deletion`` is off, the host is kept and the impact is
        logged so operators can review it before enabling the setting.
        """
        if get_plugin_settings().allow_inherited_deletion:
            return False
        logger.warning(
            'Not deleting Zabbix host for %s on %s (hostid %s): %s requires deletion, but allow_inherited_deletion is disabled. Enable it to let nbxsync remove the host and its history.',
            self.instance,
            zabbixserver,
            hostid or 'unknown',
            reason,
        )
        return True

    def _record_partial_failure(self, assignment, message):
        """Remember a recoverable failure and surface it on the assignment row."""
        self.partial_errors.append(message)
        logger.warning('%s: %s', self.instance, message)
        if assignment is not None:
            assignment.update_sync_info(success=False, message=message[:3000])

    def _raise_on_partial_failure(self):
        """Fail the job when independent work completed but something was lost.

        Without this, an operator sees a successful reconciliation for a host
        whose interfaces or template linkage never made it into Zabbix.
        """
        errors = getattr(self, 'partial_errors', [])
        if not errors:
            return
        summary = '; '.join(errors[:10])
        if len(errors) > 10:
            summary = f'{summary}; (+{len(errors) - 10} more)'
        raise RuntimeError(f'Partial sync failure for {self.instance}: {summary}')

    def _retire_unassigned_bindings(self, assigned_server_ids):
        for binding in iter_host_bindings(self.instance):
            if binding.zabbixserver_id in assigned_server_ids:
                continue
            if not binding.zabbixserver.sync_enabled:
                continue
            if self._deletion_blocked('no remaining Zabbix server assignment', binding.zabbixserver, binding.hostid):
                continue
            proxy = HostBindingDeleteProxy(binding, assigned_object=self.instance)
            try:
                safe_delete(HostSync, proxy, extra_args={'all_objects': {'_instance': self.instance}})
            except Exception as e:
                self._record_partial_failure(None, f'Failed to retire binding {binding}: {e}')

    def delete_host(self, assignment):
        safe_delete(HostSync, assignment, extra_args={'all_objects': {'_instance': self.instance}})

    def _resolve_all_objects(self, assignment):
        """Resolve the assignments for one Zabbix server, OOB filtering included.

        Every caller must see the same interface set: an interface that sync_host
        skips but verify_hostinterfaces still considers unexpected would be
        deleted from Zabbix on every run and recreated on the next one.
        """
        all_objects = get_assigned_zabbixobjects(self.instance, zabbixserver=assignment.zabbixserver)
        all_objects['_instance'] = self.instance

        # use_oob_ip interfaces cannot be synced when the object has no OOB IP:
        # a VM never has one, and a device may not have one yet. Syncing them
        # anyway would link SNMP templates to a host without an SNMP interface.
        has_oob_ip = bool(getattr(self.instance, 'oob_ip', None))
        unresolvable = [hi for hi in all_objects['hostinterfaces'] if getattr(hi, 'use_oob_ip', False) and not has_oob_ip]
        if unresolvable:
            all_objects['hostinterfaces'] = [hi for hi in all_objects['hostinterfaces'] if hi not in unresolvable]
            if get_plugin_settings().allow_inherited_deletion:
                logger.warning(
                    'Skipping %s OOB interface(s) for %s: no out-of-band IP. Any interface already present in Zabbix will be removed because allow_inherited_deletion is enabled.',
                    len(unresolvable),
                    self.instance,
                )
            else:
                # Keep whatever Zabbix already has: an OOB IP that disappeared
                # from NetBox is usually a data-entry gap, not an instruction to
                # discard the interface and its item history.
                all_objects['retained_hostinterfaces'] = unresolvable
                logger.warning(
                    'Skipping %s OOB interface(s) for %s: no out-of-band IP. Existing Zabbix interfaces are retained; enable allow_inherited_deletion to let nbxsync remove them.',
                    len(unresolvable),
                    self.instance,
                )

        return all_objects

    def verify_hostinterfaces(self, assignment):
        all_objects = self._resolve_all_objects(assignment)
        run_zabbix_operation(HostSync, assignment, 'verify_hostinterfaces', extra_args={'all_objects': all_objects})

    def check_default_hostinterface(self, assignment):
        all_objects = self._resolve_all_objects(assignment)
        run_zabbix_operation(HostSync, assignment, 'check_default_hostinterface', extra_args={'all_objects': all_objects})

    def sync_host(self, assignment):
        try:
            all_objects = self._resolve_all_objects(assignment)
            # Add the assigned_objects attribute, so we dont have to do this expensive calculation again later on :)
            assignment.assigned_objects = all_objects
            all_objects['_instance'] = self.instance

            # Create all hostgroups (skip template-based assignments — they are
            # created on-demand during HostSync.get_groups() with the actual
            # device as render context)
            for hostgroup in all_objects['hostgroups']:
                if hasattr(hostgroup, 'is_template') and hostgroup.is_template():
                    continue
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
                logger.warning(f'Initial HostSync failed for {self.instance}: {e}')

            # Once the Host exists and we have a HostId, time to sync the interfaces
            # Sort by:
            # - interface_type (defaults should be synced first)
            # - type (group snmp, agent, jmx, etc)
            # - id (None-safe for transient ConfigGroup / hierarchy copies)
            hostid = get_managed_host_id(self.instance, assignment.zabbixserver) or assignment.hostid
            hostinterfaces_sorted = sorted(
                all_objects['hostinterfaces'],
                key=lambda hostinterface: (-int(hostinterface.interface_type == 1), hostinterface.type, hostinterface.id or 0),
            )
            for hostinterface in hostinterfaces_sorted:
                try:
                    safe_sync(HostInterfaceSync, hostinterface, extra_args={'hostid': hostid, '_instance': self.instance})
                except RuntimeError as e:
                    # Continue syncing remaining interfaces even if one fails.
                    # A common case: device inherits both Agent and SNMP
                    # interfaces but the SNMP credentials are wrong — this
                    # should not prevent the Agent interface and templates
                    # from being synced. The failure is still reported at the
                    # end of the job so it cannot pass as a successful sync.
                    self._record_partial_failure(assignment, f'HostInterfaceSync failed for interface {hostinterface}: {e}')

            # Reconcile main flags after individual IF updates. A main-flag flip
            # can leave two defaults briefly when HostInterfaceSync updates one
            # interface at a time; check_default_hostinterface applies the
            # atomic host.update repair. Safe when NetBox has no default for a
            # type that still exists remotely (guarded inside check_default).
            try:
                run_zabbix_operation(
                    HostSync,
                    assignment,
                    'check_default_hostinterface',
                    extra_args={'all_objects': all_objects},
                )
            except Exception as e:
                self._record_partial_failure(assignment, f'check_default_hostinterface failed: {e}')

            # Final HostSync to link templates etc — a template conflict here
            # (e.g. "Cannot inherit item with key snmptrap.fallback") must not
            # abort the remaining work, but it is a real failure to report.
            try:
                safe_sync(HostSync, assignment, extra_args={'all_objects': all_objects})
            except Exception as e:
                self._record_partial_failure(assignment, f'Final HostSync failed: {e}')

        except Exception as e:
            raise RuntimeError(f'Unexpected error: {e}')
