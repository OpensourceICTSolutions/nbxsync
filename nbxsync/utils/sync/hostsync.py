import logging
import re
from datetime import datetime, timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django_rq import get_queue

from .syncbase import ZabbixSyncBase
from nbxsync.choices import HostInterfaceRequirementChoices, ZabbixHostInterfaceSNMPVersionChoices, ZabbixHostInterfaceTypeChoices, ZabbixInterfaceSNMPV3SecurityLevelChoices
from nbxsync.choices.syncsot import SyncSOT
from nbxsync.choices.zabbixstatus import ZabbixHostStatus
from nbxsync.models import ZabbixHostInterface, ZabbixMaintenance, ZabbixMaintenanceObjectAssignment, ZabbixMaintenancePeriod
from nbxsync.utils.host_binding import backfill_or_resolve_conflict, delete_host_binding, delete_host_binding_by_id, get_host_binding, set_host_binding
from nbxsync.utils.sync.hostgroupsync import ensure_parent_hostgroups
from nbxsync.utils.sync.hostinterfacesync import HostInterfaceSync

logger = logging.getLogger(__name__)


class HostSync(ZabbixSyncBase):
    id_field = 'hostid'
    sot_key = 'host'

    def api_object(self):
        return self.api.host

    def _get_sync_target(self):
        """Return the Device/VM being synced, falling back to the assignment's assigned_object.

        When a ZabbixServerAssignment is inherited from a Site, Platform, etc.,
        ``self.obj.assigned_object`` is that higher-level object, not the Device.
        The sync engine passes the actual instance via ``all_objects['_instance']``
        so that status, description, serial, and other device-level attributes
        resolve correctly.
        """
        return self.context.get('all_objects', {}).get('_instance') or self.obj.assigned_object

    def _resolve_binding(self):
        """Resolve a durable hostid for the sync target.

        Order:
        1. Existing ``ZabbixHostBinding`` for the (server, instance) pair.
        2. Legacy ``ZabbixServerAssignment.hostid`` on a direct assignment.
        3. Backfill an existing Zabbix host that carries the managed
           ``objtag_type``/``objtag_id`` identity tags.

        The resolved hostid is written to ``self.obj.hostid`` so the rest of
        the sync engine can continue to use the existing id-based paths.
        """
        sync_target = self._get_sync_target()
        zabbixserver = self.obj.zabbixserver

        binding = get_host_binding(sync_target, zabbixserver)
        if binding:
            self.obj.hostid = binding.hostid
            return

        if self.obj.hostid:
            self._migrate_legacy_hostid(sync_target, zabbixserver)
            return

        # No binding and no legacy id: try to adopt an existing managed host.
        try:
            technical_name = self.sanitize_string(input_str=str(self.get_name_value()))
            existing_hostid = backfill_or_resolve_conflict(sync_target, zabbixserver, self.api, hostname=technical_name)
        except RuntimeError:
            raise
        if existing_hostid:
            self.obj.hostid = existing_hostid
            set_host_binding(sync_target, zabbixserver, existing_hostid, hostname=technical_name)

    def _migrate_legacy_hostid(self, sync_target, zabbixserver):
        """Move a direct-assignment hostid into a durable binding."""
        hostid = int(self.obj.hostid)
        binding = set_host_binding(sync_target, zabbixserver, hostid, hostname=str(self.get_name_value()))
        self.obj.hostid = binding.hostid

    def _persist_binding(self):
        """Store/update the binding after a successful create or update."""
        sync_target = self._get_sync_target()
        hostid = self.get_id()
        if not hostid:
            return
        set_host_binding(sync_target, self.obj.zabbixserver, int(hostid), hostname=str(self.get_name_value()))

    def _clear_direct_hostid(self):
        """After migrating to bindings, clear the legacy hostid from direct assignments."""
        if not self._should_persist():
            return
        if not self.obj.pk:
            return
        if self.obj.hostid:
            self.obj.hostid = None
            self.obj.save(update_fields=['hostid'])

    def _zabbix_host_missing(self):
        """Return True if the current hostid has no matching remote host."""
        hostid = self.get_id()
        if not hostid:
            return True
        return not self.find_by_id()

    def set_id(self, value):
        super().set_id(value)
        self._persist_binding()

    def sync_to_zabbix(self, object_id):
        super().sync_to_zabbix(object_id)
        self._persist_binding()

    def sync(self):
        self._resolve_binding()
        super().sync()
        self._clear_direct_hostid()

    def get_base_name(self):
        # If the object has the "name" attribute, only return that (Device). If not (cornercase?), return the display string
        sync_target = self._get_sync_target()
        if hasattr(sync_target, 'name'):
            return sync_target.name

        return str(sync_target)

    def get_name_value(self):
        sync_target = self._get_sync_target()
        base_name = self.get_base_name()
        cf_name = getattr(self.pluginsettings, 'custom_field_hostname', '')
        if cf_name and hasattr(sync_target, 'custom_field_data'):
            cf_value = sync_target.custom_field_data.get(cf_name)
            if cf_value:
                return str(cf_value)
        return base_name

    def get_display_name(self):
        sync_target = self._get_sync_target()
        base_name = self.get_base_name()
        cf_name = getattr(self.pluginsettings, 'custom_field_display_name', '')
        if cf_name and hasattr(sync_target, 'custom_field_data'):
            cf_value = sync_target.custom_field_data.get(cf_name)
            if cf_value:
                return str(cf_value)
        return base_name

    def find_by_name(self):
        return self.api_object().get(filter={'host': self.sanitize_string(input_str=str(self.get_name_value()))})

    def get_create_params(self):
        sync_target = self._get_sync_target()
        status = sync_target.status
        object_type = sync_target._meta.model_name  # "device" or "virtualmachine"
        status_mapping = getattr(self.pluginsettings.statusmapping, object_type, {})
        zabbix_status = status_mapping.get(status)

        host_status = 0  # Active/monitored
        if zabbix_status == ZabbixHostStatus.DISABLED:
            host_status = 1  # Disabled/Not monitored

        self.verify_maintenancewindow()

        return {
            'host': self.sanitize_string(input_str=str(self.get_name_value())),
            'name': self.get_display_name(),
            'groups': self.get_groups(),
            'status': host_status,
            'description': sync_target.description or '',
            **self.get_proxy_or_proxygroup(),
            **self.get_hostinterface_attributes(),
            **self.get_tag_attributes(),
            **self.get_macros(),
            **self.get_hostinventory(),
        }

    def get_update_params(self, **kwargs):
        self.templates = self.get_template_attributes()
        templates_clear = self.get_templates_clear_attributes()

        # Start by creating the full merged dict using unpacking
        params = {
            **self.get_create_params(),  # base params
            **self.templates,  # add templates
            **templates_clear,  # add template clear overrides
        }

        # Add hostid separately
        params['hostid'] = self.obj.hostid

        return params

    def result_key(self):
        return 'hostids'

    def sync_from_zabbix(self, data):
        return {}
        # TODO: Fix
        # self.obj.proxy_groupid = data['proxy_groupid']
        # self.obj.name = data.get('name', self.obj.name)
        # self.obj.description = data.get('description', '')
        # self.obj.failover_delay = data.get('failover_delay')
        # self.obj.min_online = data.get('min_online')
        # self.obj.save()
        # self.obj.update_sync_info(success=True, message='')

    def get_proxy_or_proxygroup(self):
        result = {'monitored_by': 0}
        if self.obj.zabbixproxy:
            result['monitored_by'] = 1  # Proxy
            result['proxyid'] = self.obj.zabbixproxy.proxyid
        if self.obj.zabbixproxygroup:
            result['monitored_by'] = 2  # ProxyGroup
            result['proxy_groupid'] = self.obj.zabbixproxygroup.proxy_groupid

        return result

    def get_defined_macros(self):
        result = []
        for macro in self.context.get('all_objects', {}).get('macros', []) or []:
            rendered_value, _ = macro.render(object=self._get_sync_target())
            result.append(
                {
                    'macro': str(macro),
                    'type': macro.zabbixmacro.type,
                    'description': macro.zabbixmacro.description,
                    'value': rendered_value,
                }
            )

        hostmacro_sot = getattr(self.pluginsettings.sot, 'hostmacro', None)
        if hostmacro_sot == SyncSOT.ZABBIX:
            intended_macros = {macro['macro'] for macro in result if 'macro' in macro}
            current = self.api.host.get(output=['hostid'], hostids=self.obj.hostid, selectMacros=['macro', 'value', 'description', 'type'])
            current_macros = current[0].get('macros', []) if current else []

            for macro in current_macros:
                if macro.get('macro') not in intended_macros:
                    result.append(
                        {
                            'macro': macro['macro'],
                            'value': macro.get('value', ''),
                            'description': macro.get('description', ''),
                            'type': int(macro.get('type', 0)),
                        }
                    )

        return result

    def get_snmp_macros(self):
        result = []
        hostinterfaces = self.context.get('all_objects', {}).get('hostinterfaces', []) or []
        snmpconf = self.pluginsettings.snmpconfig

        for hostinterface in hostinterfaces:
            # Skip all non-SNMP interfaces
            if hostinterface.type != ZabbixHostInterfaceTypeChoices.SNMP:
                continue

            if hostinterface.snmp_version in [
                ZabbixHostInterfaceSNMPVersionChoices.SNMPV1,
                ZabbixHostInterfaceSNMPVersionChoices.SNMPV2,
            ]:
                if hostinterface.snmp_pushcommunity:
                    result.append(
                        {
                            'macro': snmpconf.snmp_community,
                            'value': hostinterface.snmp_community,
                            'description': 'SNMPv2 Community',
                            'type': 1,  # Secret macro
                        }
                    )

            if hostinterface.snmp_version == ZabbixHostInterfaceSNMPVersionChoices.SNMPV3:
                if hostinterface.snmpv3_security_level in [
                    ZabbixInterfaceSNMPV3SecurityLevelChoices.AUTHNOPRIV,
                    ZabbixInterfaceSNMPV3SecurityLevelChoices.AUTHPRIV,
                ]:
                    if hostinterface.snmp_pushcommunity:
                        result.append(
                            {
                                'macro': snmpconf.snmp_authpass,
                                'value': hostinterface.snmpv3_authentication_passphrase,
                                'description': 'SNMPv3 Authentication Passphrase',
                                'type': 1,  # Secret macro
                            }
                        )
                if hostinterface.snmpv3_security_level == ZabbixInterfaceSNMPV3SecurityLevelChoices.AUTHPRIV:
                    if hostinterface.snmp_pushcommunity:
                        result.append(
                            {
                                'macro': snmpconf.snmp_privpass,
                                'value': hostinterface.snmpv3_privacy_passphrase,
                                'description': 'SNMPv3 Privacy Passphrase',
                                'type': 1,  # Secret macro
                            }
                        )

        return result

    def get_macros(self):
        all_macros = self.get_defined_macros()
        snmp_macros = self.get_snmp_macros()

        macros_by_name = {}

        # It is possible to create a macro with the same name as SNMPCONFIG.SNMP_COMMUNITY
        # This would result in 2 macros with the same name, something Zabbix doesn't accept
        # So, in order to solve this....

        # Put SNMP-generated macros in first...
        for macro in snmp_macros:
            macros_by_name[macro['macro']] = macro

        # Then overlay regular macros so the user-configured macro's is preferred
        for macro in all_macros:
            macros_by_name[macro['macro']] = macro

        return {'macros': list(macros_by_name.values())}

    def get_hostinterface_attributes(self):
        result = {}
        for hostinterface in self.context.get('all_objects', {}).get('hostinterfaces', []) or []:
            if hostinterface.type == ZabbixHostInterfaceTypeChoices.AGENT:
                result['tls_connect'] = hostinterface.tls_connect
                result['tls_accept'] = 0
                for x in hostinterface.tls_accept:
                    # Bitwise OR, not just sum().
                    result['tls_accept'] |= x
                result['tls_issuer'] = hostinterface.tls_issuer
                result['tls_subject'] = hostinterface.tls_subject
                result['tls_psk_identity'] = hostinterface.tls_psk_identity
                result['tls_psk'] = hostinterface.tls_psk

            if hostinterface.type == ZabbixHostInterfaceTypeChoices.IPMI:
                result['ipmi_authtype'] = hostinterface.ipmi_authtype
                result['ipmi_password'] = hostinterface.ipmi_password
                result['ipmi_privilege'] = hostinterface.ipmi_privilege
                result['ipmi_username'] = hostinterface.ipmi_username
        return result

    def get_hostinterface_types(self):
        # use_oob_ip interfaces without a resolvable OOB IP are filtered out of
        # hostinterfaces once in SyncHostJob._resolve_all_objects(). When
        # inheritance-driven deletion is off they are kept in
        # retained_hostinterfaces so verify_hostinterfaces will not delete the
        # remote interface. Template gating must see those same types: otherwise
        # an SNMP-required template is cleared while the OOB SNMP interface is
        # intentionally retained, silently dropping monitoring.
        hostinterfaces = self.context.get('all_objects', {}).get('hostinterfaces', []) or []
        retained = self.context.get('all_objects', {}).get('retained_hostinterfaces', []) or []
        return list({interface.type for interface in list(hostinterfaces) + list(retained)})

    def get_templates_clear_attributes(self):
        result = []
        if not self.obj.hostid:
            return {}

        # Get currently assigned templates from Zabbix
        currently_assigned_templates = self.api.template.get(hostids=int(self.obj.hostid))

        # Flatten current templates to a set of integers
        current_ids = {int(current_template['templateid']) for current_template in currently_assigned_templates}

        # Extract actual template list from the dict
        to_be_templates = self.templates.get('templates', [])

        intended_ids = set()
        for template in to_be_templates:
            if isinstance(template, dict) and 'templateid' in template:
                intended_ids.add(int(template['templateid']))

        # Find templates that need to be cleared (currently assigned but not intended)
        templates_to_clear = current_ids - intended_ids

        for templateid in templates_to_clear:
            result.append({'templateid': templateid})

        hosttemplate_sot = getattr(self.pluginsettings.sot, 'hosttemplate', None)
        if hosttemplate_sot == SyncSOT.NETBOX:
            # Clear the templates, as Netbox contains the Truth
            return {'templates_clear': result}

        if hosttemplate_sot == SyncSOT.ZABBIX:
            # As Zabbix is the 'SoT', we'll just accept the unaccounted templates
            for template in result:
                self.templates['templates'].append(template)
            return {}

    def get_template_attributes(self):
        result = []
        hostinterface_types = set(self.get_hostinterface_types() or [])

        for assigned_template in self.context.get('all_objects', {}).get('templates', []) or []:
            required = set(assigned_template.zabbixtemplate.interface_requirements or [])

            # Extract special modifiers
            has_none = HostInterfaceRequirementChoices.NONE in required
            has_any = HostInterfaceRequirementChoices.ANY in required
            actual_required = required - {HostInterfaceRequirementChoices.NONE, HostInterfaceRequirementChoices.ANY}

            # NONE means no interfaces are required, so always OK
            if has_none and not actual_required and not has_any:
                pass

            # If ANY is present, host must have at least one interface
            elif has_any and not hostinterface_types:
                continue

            # Now check actual requirements (excluding NONE/ANY)
            elif actual_required and not actual_required.issubset(hostinterface_types):
                continue

            # Passed all checks
            result.append({'templateid': assigned_template.zabbixtemplate.templateid})

        return {'templates': result}

    def get_tag_attributes(self):
        sync_target = self._get_sync_target()
        status = sync_target.status
        object_type = sync_target._meta.model_name  # "device" or "virtualmachine"
        status_mapping = getattr(self.pluginsettings.statusmapping, object_type, {})
        zabbix_status = status_mapping.get(status)

        result = []
        exclude_tag = getattr(self.pluginsettings, 'exclude_tag', '')
        for assigned_tag in self.context.get('all_objects', {}).get('tags', []) or []:
            # Skip the exclusion tag before rendering — it is a sync-time
            # signal, not a Zabbix host tag. Filtering here avoids
            # unnecessary Jinja2 rendering of a tag that will never reach
            # Zabbix.
            if exclude_tag and assigned_tag.zabbixtag.tag == exclude_tag:
                continue
            value, _ = assigned_tag.render(object=sync_target)
            result.append({'tag': assigned_tag.zabbixtag.tag, 'value': value})

        # Deduplicate tags by (tag, value). The same tag value can be
        # resolved from multiple sources in the inheritance chain (e.g.
        # environment=Production inherited from both a specific role
        # and the parent Server role), which Zabbix rejects.
        seen = set()
        deduped = []
        for tag in result:
            key = (tag['tag'], tag['value'])
            if key not in seen:
                seen.add(key)
                deduped.append(tag)
        result = deduped

        if zabbix_status == ZabbixHostStatus.ENABLED_NO_ALERTING:
            result.append({'tag': self.pluginsettings.no_alerting_tag, 'value': str(self.pluginsettings.no_alerting_tag_value)})

        if self.pluginsettings.attach_objtag:
            result.append({'tag': self.pluginsettings.objtag_type, 'value': str(type(sync_target).__name__).lower()})
            result.append({'tag': self.pluginsettings.objtag_id, 'value': str(sync_target.id)})

        return {'tags': result}

    def get_groups(self):
        groups = []
        errors = []
        for group in self.obj.assigned_objects.get('hostgroups', []):
            # 1) If we already know the Zabbix groupid, use it (fast path).
            gid = getattr(getattr(group, 'zabbixhostgroup', None), 'groupid', None)
            if gid:
                groups.append({'groupid': gid})
                continue

            # 2) Otherwise, try to resolve by name (e.g., for template-like objects).
            name, status = ('', False)
            try:
                name, status = group.render(object=self._get_sync_target())
            except Exception as exc:
                errors.append(f'Failed to render hostgroup for {self._get_sync_target()}: {exc}')
                continue
            if not (status and name):
                errors.append(f'Hostgroup for {self._get_sync_target()} rendered empty; refusing to omit it silently')
                continue

            try:
                zbx_result = self.api.hostgroup.get(filter={'name': name}) or []
                if zbx_result:
                    groups.append({'groupid': zbx_result[0]['groupid']})
                    continue
                # Materialize nested parents before the leaf so the subgroup
                # inherits the parent's user-group permissions (see
                # ensure_parent_hostgroups).
                ensure_parent_hostgroups(self.api, name)
                created = self.api.hostgroup.create({'name': name})
                gid = created.get('groupids', [None])[0]
                if gid:
                    groups.append({'groupid': gid})
                else:
                    errors.append(f'Zabbix did not return a groupid when creating hostgroup "{name}"')
            except Exception as exc:
                errors.append(f'Failed to resolve/create hostgroup "{name}": {exc}')

        if errors:
            raise RuntimeError('; '.join(errors))
        return groups

    def get_hostinventory(self):
        hostinventory = self.context.get('all_objects', {}).get('hostinventory', None)
        sync_target = self._get_sync_target()
        inventory = {}
        inventory_mode = 0

        if hostinventory:
            inventory_mode = hostinventory.inventory_mode or 0

            # Override the context object with the actual device/VM for Jinja2 rendering
            for field_name, (rendered_value, success) in hostinventory.render_all_fields(object=sync_target).items():
                if success and rendered_value:
                    inventory[field_name] = rendered_value

        result = {'inventory_mode': inventory_mode}
        if inventory:
            result['inventory'] = inventory

        return result

    def verify_maintenancewindow(self):
        sync_target = self._get_sync_target()
        status = sync_target.status
        object_type = sync_target._meta.model_name  # "device" or "virtualmachine"
        status_mapping = getattr(self.pluginsettings.statusmapping, object_type, {})
        zabbix_status = status_mapping.get(status)

        object_ct = ContentType.objects.get_for_model(sync_target)
        mw_assignments = ZabbixMaintenanceObjectAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=sync_target.id)

        if zabbix_status != ZabbixHostStatus.ENABLED_IN_MAINTENANCE:
            for assignment in mw_assignments:
                # If its a automatically created assignment, just delete the maintenance window
                # This will trigger the deletion of the assignment as well.
                if assignment.zabbixmaintenance.automatic:
                    assignment.zabbixmaintenance.delete()

            return

        # Determine if a maintenance object should be created
        # If there isn't any assignment which has a maintenance attached that has been created automatically
        # a window should be created
        should_create_maintenance_object = not any(mw_assignment.zabbixmaintenance.automatic for mw_assignment in mw_assignments)

        if should_create_maintenance_object:
            now = datetime.now()
            end_date = now + timedelta(seconds=int(self.pluginsettings.maintenance_window_duration))
            # Create the Maintenance object
            maintenance = ZabbixMaintenance(name=f'[AUTOMATIC] {str(sync_target)}', description='Automatically created maintenance object due to the object status', automatic=True, active_since=now, active_till=end_date, zabbixserver=self.obj.zabbixserver)
            maintenance.save()

            # Assign this host to the Maintenance object
            ZabbixMaintenanceObjectAssignment(zabbixmaintenance=maintenance, assigned_object_type=object_ct, assigned_object_id=sync_target.id).save()
            # And create the maintenance period
            seconds_of_day = now.hour * 3600 + now.minute * 60 + now.second
            ZabbixMaintenancePeriod(zabbixmaintenance=maintenance, start_date=now, start_time=seconds_of_day, period=int(self.pluginsettings.maintenance_window_duration)).save()

            # Now all objects are in place, fire the sync job
            queue = get_queue('low')
            queue.enqueue_job(
                queue.create_job(
                    func='nbxsync.worker.syncmaintenance',
                    args=[maintenance],
                    timeout=9000,
                )
            )

    def _clear_deleted_host_state(self, sync_target, zabbixserver):
        binding_id = getattr(self.obj, 'binding_id', None)
        if binding_id is not None:
            delete_host_binding_by_id(binding_id)
        elif sync_target is not None:
            delete_host_binding(sync_target, zabbixserver)

        if binding_id is None and self._should_persist():
            try:
                self.obj.hostid = None
                self.obj.save()
            except (ValidationError, AttributeError):
                pass

        if sync_target is not None:
            try:
                object_ct = ContentType.objects.get_for_model(sync_target)
                ZabbixHostInterface.objects.filter(
                    assigned_object_type=object_ct,
                    assigned_object_id=sync_target.pk,
                    zabbixserver=zabbixserver,
                ).update(interfaceid=None)
            except Exception:
                pass

    def delete(self):  # noqa: C901
        """Delete a host by durable ID and remove its binding only after success."""
        sync_target = self._get_sync_target()
        zabbixserver = self.obj.zabbixserver

        binding = get_host_binding(sync_target, zabbixserver) if sync_target is not None else None
        hostid = binding.hostid if binding else self.obj.hostid
        if not hostid:
            try:
                self.obj.update_sync_info(success=False, message='Host already deleted or missing host ID.')
            except Exception:
                pass
            return

        try:
            api_object = self.api_object()
            get_remote_hosts = getattr(api_object, 'get', None)
            remote_hosts = get_remote_hosts(hostids=[hostid]) if callable(get_remote_hosts) else [{'hostid': hostid}]
            if isinstance(remote_hosts, dict):
                remote_hosts = remote_hosts.get('result', [])

            if not remote_hosts:
                self._clear_deleted_host_state(sync_target, zabbixserver)
                try:
                    self.obj.update_sync_info(success=True, message='Host was already absent from Zabbix.')
                except Exception:
                    pass
                return

            if sync_target is not None:
                object_ct = ContentType.objects.get_for_model(sync_target)
                maintenances = self.api.maintenance.get(hostids=[hostid], selectHosts='extend')
                for maintenance in maintenances:
                    if len(maintenance['hosts']) > 1:
                        hosts = [{'hostid': host['hostid']} for host in maintenance['hosts'] if int(host['hostid']) != int(hostid)]
                        self.api.maintenance.update(maintenanceid=maintenance['maintenanceid'], hosts=hosts)
                        ZabbixMaintenanceObjectAssignment.objects.filter(
                            maintenanceid=maintenance['maintenanceid'],
                            assigned_object_type=object_ct,
                            assigned_object_id=sync_target.pk,
                        ).delete()
                    else:
                        self.api.maintenance.delete([maintenance['maintenanceid']])
                        ZabbixMaintenance.objects.get(maintenanceid=maintenance['maintenanceid']).delete()

            api_object.delete([hostid])
            self._clear_deleted_host_state(sync_target, zabbixserver)

            try:
                self.obj.update_sync_info(success=True, message='Host deleted from Zabbix.')
            except Exception:
                pass
        except Exception as exc:
            try:
                self.obj.update_sync_info(success=False, message=f'Failed to delete host: {exc}')
            except Exception:
                pass
            raise RuntimeError(f'Failed to delete host {hostid} from Zabbix: {exc}') from exc

    def _ensure_hostid(self):
        """Populate ``self.obj.hostid`` from a durable binding when the assignment row was cleared.

        ``check_default_hostinterface`` and ``verify_hostinterfaces`` are invoked
        as standalone operations (not via ``sync()``), so they never run
        ``_resolve_binding()``. After ``_clear_direct_hostid`` the assignment
        hostid is None even though the binding still holds the real id.
        """
        if self.obj.hostid:
            return
        sync_target = self._get_sync_target()
        binding = get_host_binding(sync_target, self.obj.zabbixserver)
        if binding and binding.hostid:
            self.obj.hostid = binding.hostid

    def check_default_hostinterface(self):  # noqa: C901
        self._ensure_hostid()
        if not self.obj.hostid:
            return

        hostid = str(int(self.obj.hostid))
        netbox_hostinterfaces = self.context.get('all_objects', {}).get('hostinterfaces', []) or []
        zabbix_hostinterfaces = self.api.hostinterface.get(hostids=hostid)

        netbox_default_obj_by_type = {}
        netbox_default_id_by_type = {}
        zabbix_default_id_by_type = {}

        # Loop through all Netbox Host Interfaces and get the default interface id per type
        for netbox_hostinterface in netbox_hostinterfaces:
            if int(getattr(netbox_hostinterface, 'interface_type', 0)) == 1:
                netbox_default_obj_by_type[int(netbox_hostinterface.type)] = netbox_hostinterface
                interface_id = None
                if getattr(netbox_hostinterface, 'interfaceid', None):
                    interface_id = str(int(netbox_hostinterface.interfaceid))

                netbox_default_id_by_type[int(netbox_hostinterface.type)] = interface_id

        # Loop through all Zabbix Host Interfaces and get the default interface id per type
        for zabbix_hostinterface in zabbix_hostinterfaces:
            if int(zabbix_hostinterface.get('main', 0)) == 1:
                zabbix_default_id_by_type[int(zabbix_hostinterface.get('type'))] = str(int(zabbix_hostinterface.get('interfaceid')))

        all_types = set(netbox_default_id_by_type) | set(zabbix_default_id_by_type)

        for hostinterface_type in sorted(all_types):
            nb_default_hostinterface_obj = netbox_default_obj_by_type.get(hostinterface_type)
            nb_default_hostinterface_id = netbox_default_id_by_type.get(hostinterface_type)
            zbx_default_hostinterfaceid = zabbix_default_id_by_type.get(hostinterface_type)

            if not zbx_default_hostinterfaceid:
                # No zabbix interfaces?
                # Nothing to do here in that case
                continue

            if nb_default_hostinterface_id != zbx_default_hostinterfaceid:
                # Zabbix still has a default of this type, but NetBox no longer
                # does (e.g. OOB SNMP removed from the expected set and waiting
                # for verify_hostinterfaces to delete it). Nothing to flip.
                if not nb_default_hostinterface_obj:
                    continue

                instance = self.context.get('all_objects', {}).get('_instance')
                # Resolve an existing interface before creating one. Inherited
                # interface rows intentionally have no persisted interfaceid;
                # blindly creating a replacement makes host.update try to delete
                # the original interface, which Zabbix rejects while items use it.
                if not nb_default_hostinterface_id:
                    syncer = HostInterfaceSync(self.api, nb_default_hostinterface_obj, hostid=hostid, _instance=instance)
                    matches = syncer.find_by_name()
                    hostinterface_id = matches[0].get('interfaceid') if matches else None

                    if not hostinterface_id:
                        params = syncer.get_create_params()
                        if not params:
                            continue

                        params['main'] = 0  # create as NON-default
                        created = self.api.hostinterface.create(**params)
                        hostinterface_id = created.get('interfaceids', [None])[0]
                        if not hostinterface_id:
                            raise RuntimeError(f'Failed to create interface for type={hostinterface_type}: {created}')

                    nb_default_hostinterface_obj.interfaceid = int(hostinterface_id)
                    # Transient ConfigGroup clones are pk=None in-memory copies.
                    # Saving them would INSERT a new HostInterface row without
                    # ConfigGroup provenance. Keep the interfaceid on the
                    # working object only; the next sync resolves by identity.
                    if not getattr(nb_default_hostinterface_obj, '_is_inherited_copy', False) and nb_default_hostinterface_obj.pk:
                        nb_default_hostinterface_obj.save()

                    # update local variable so the compare is correct for the flip step
                    nb_default_hostinterface_id = str(int(hostinterface_id))

                # Some very 'complicated' logic to flip the main
                # As Zabbix can have only 1 default/main interface at the time, we must update all interfaces at once
                # As such, we loop through all hostinterfaces, and use the HostInterfaceSync module to get the create params
                # That way, we can update all interfaces at once
                desired_hostinterfaces = []
                for netbox_hostinterface in netbox_hostinterfaces:
                    syncer = HostInterfaceSync(self.api, netbox_hostinterface, hostid=hostid, _instance=instance)
                    params = syncer.get_update_params()
                    if not params or not params.get('interfaceid'):
                        continue
                    desired_hostinterfaces.append(params)

                if desired_hostinterfaces:
                    self.api.host.update(hostid=hostid, interfaces=desired_hostinterfaces)
        return

    def verify_hostinterfaces(self):
        # If there is no hostid, no need to continue - so fail early
        self._ensure_hostid()
        if not self.obj.hostid:
            return {}

        # Extract the currently expected interfaces
        expected_hostinterfaces = self.context.get('all_objects', {}).get('hostinterfaces', []) or []
        # Interfaces that could not be synced this run (e.g. an OOB interface on
        # a device whose oob_ip was cleared) are retained rather than deleted.
        retained_hostinterfaces = self.context.get('all_objects', {}).get('retained_hostinterfaces', []) or []
        considered_hostinterfaces = list(expected_hostinterfaces) + list(retained_hostinterfaces)

        # Include persisted interfaceids from both expected and retained rows.
        # A previously synced OOB interface kept in retained_hostinterfaces still
        # carries its interfaceid; omitting it here would delete the remote IF.
        expected_ids = {int(hi.interfaceid) for hi in considered_hostinterfaces if hi.interfaceid}

        # Get currently assigned hostinterface from Zabbix.
        # output must be the string 'extend' — a one-element list ['extend'] is
        # treated as a field name, so type/main/port come back empty and every
        # transient ConfigGroup/hierarchy interface fails identity matching and
        # is deleted on the same sync that created it.
        current_hostinterfaces = self.api.hostinterface.get(output='extend', hostids=self.obj.hostid)

        # Interfaces inherited from a ConfigGroup are transient copies without a
        # persisted interfaceid, so they must be recognised by what Zabbix stores
        # instead. Deleting them here would remove an interface that the very
        # next sync recreates, and fail outright once items are linked to it.
        # Match the ConfigGroup identity helper: type + main role + connect mode
        # + port + dns. IP is omitted here because OOB interfaces resolve it at
        # sync time and would otherwise look "stale" every run.
        expected_identities = {
            (
                int(hi.type),
                int(hi.interface_type),
                int(hi.useip),
                str(hi.port),
                str(hi.dns or ''),
            )
            for hi in considered_hostinterfaces
            if not hi.interfaceid
        }

        # Inherited server assignments must not persist ORM rows, but remote
        # stale-interface cleanup is still required for Site-level proxies.
        # Gate that destructive remote work on allow_inherited_deletion.
        if not self._should_persist() and not self.pluginsettings.allow_inherited_deletion:
            return

        for current_hostinterface in current_hostinterfaces:
            interfaceid = int(current_hostinterface['interfaceid'])
            if interfaceid in expected_ids:
                continue
            identity = (
                int(current_hostinterface.get('type', 0)),
                int(current_hostinterface.get('main', 0)),
                int(current_hostinterface.get('useip', 0)),
                str(current_hostinterface.get('port', '')),
                str(current_hostinterface.get('dns', '') or ''),
            )
            if identity in expected_identities:
                continue
            self.api.hostinterface.delete(interfaceid)

    def sanitize_string(self, input_str, replacement='_'):
        """
        Replaces all characters in input_str that do NOT match [0-9a-zA-Z_. \\-] with the replacement character.

        Args:
            input_str (str): The input string to be sanitized.
            replacement (str): Character to replace unallowed characters with.

        Returns:
            str: Sanitized string.
        """
        # Only allowed: digits, letters, _, ., space, and -
        sanitized = re.sub(r'[^0-9a-zA-Z_. \-]', replacement, input_str)
        return sanitized
