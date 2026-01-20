import re
from datetime import datetime, timedelta

from django_rq import get_queue
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from .syncbase import ZabbixSyncBase
from nbxsync.choices import HostInterfaceRequirementChoices, ZabbixHostInterfaceSNMPVersionChoices, ZabbixHostInterfaceTypeChoices, ZabbixInterfaceSNMPV3SecurityLevelChoices
from nbxsync.choices.syncsot import SyncSOT
from nbxsync.choices.zabbixstatus import ZabbixHostStatus
from nbxsync.models import ZabbixHostInterface, ZabbixMaintenance, ZabbixMaintenancePeriod, ZabbixMaintenanceObjectAssignment


class HostSync(ZabbixSyncBase):
    id_field = 'hostid'
    sot_key = 'host'

    def api_object(self):
        return self.api.host

    def get_name_value(self):
        # If the object has the "name" attribute, only return that (Device). If not (cornercase?), return the display string
        if hasattr(self.obj.assigned_object, 'name'):
            return self.obj.assigned_object.name

        return str(self.obj.assigned_object)

    def get_create_params(self):
        status = self.obj.assigned_object.status
        object_type = self.obj.assigned_object._meta.model_name  # "device" or "virtualmachine"
        status_mapping = getattr(self.pluginsettings.statusmapping, object_type, {})
        zabbix_status = status_mapping.get(status)

        host_status = 0  # Active/monitored
        if zabbix_status == ZabbixHostStatus.DISABLED:
            host_status = 1  # Disabled/Not monitored

        self.verify_maintenancewindow()

        return {
            'host': self.sanitize_string(input_str=str(self.obj.assigned_object)),
            'name': str(self.obj.assigned_object),
            'groups': self.get_groups(),
            'status': host_status,
            'description': self.obj.assigned_object.description or '',
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
        for macro in self.context.get('all_objects').get('macros'):
            result.append(
                {
                    'macro': str(macro),
                    'type': macro.zabbixmacro.type,
                    'description': macro.zabbixmacro.description,
                    'value': macro.value,
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
        hostinterfaces = self.context.get('all_objects', {}).get('hostinterfaces', [])
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
        snmpconf = self.pluginsettings.snmpconfig

        all_macros = self.get_defined_macros()
        snmp_macros = self.get_snmp_macros()

        # It is possible to create a macro with the same name as SNMPCONFIG.SNMP_COMMUNITY
        # This would result in 2 macros with the same name, something Zabbix doesn't accept
        # So, in order to solve this....

        # Loop through all regular macro's
        for macro in all_macros:
            # If the regular macro has the SNMP Community as macro
            # We'll remove it from the SNMP Macros so we dont get duplicates
            if macro['macro'] == snmpconf.snmp_community:
                snmp_macros = [m for m in snmp_macros if m['macro'] != snmpconf.snmp_community]

        return {'macros': all_macros + snmp_macros}

    def get_hostinterface_attributes(self):
        result = {}
        for hostinterface in self.context.get('all_objects', {}).get('hostinterfaces', []):
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
        hostinterfaces = self.context.get('all_objects', {}).get('hostinterfaces', [])
        return list({interface.type for interface in hostinterfaces})

    def get_templates_clear_attributes(self):
        result = []
        if not self.obj.hostid:
            return {}

        # Get currently assigned templates from Zabbix
        currently_assigned_templates = self.api.template.get(hostids=int(self.obj.hostid))

        # Flatten current templates to a set of integers
        current_ids = set(int(current_template['templateid']) for current_template in currently_assigned_templates)

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

        for assigned_template in self.context.get('all_objects', {}).get('templates', []):
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
        status = self.obj.assigned_object.status
        object_type = self.obj.assigned_object._meta.model_name  # "device" or "virtualmachine"
        status_mapping = getattr(self.pluginsettings.statusmapping, object_type, {})
        zabbix_status = status_mapping.get(status)

        result = []
        for assigned_tag in self.context.get('all_objects').get('tags'):
            value, _ = assigned_tag.render()
            result.append({'tag': assigned_tag.zabbixtag.tag, 'value': value})

        if zabbix_status == ZabbixHostStatus.ENABLED_NO_ALERTING:
            result.append({'tag': self.pluginsettings.no_alerting_tag, 'value': str(self.pluginsettings.no_alerting_tag_value)})

        if self.pluginsettings.attach_objtag:
            result.append({'tag': self.pluginsettings.objtag_type, 'value': str(type(self.obj.assigned_object).__name__).lower()})
            result.append({'tag': self.pluginsettings.objtag_id, 'value': str(self.obj.assigned_object.id)})

        return {'tags': result}

    def get_groups(self):
        groups = []
        for group in self.obj.assigned_objects.get('hostgroups', []):
            # 1) If we already know the Zabbix groupid, use it (fast path).
            gid = getattr(getattr(group, 'zabbixhostgroup', None), 'groupid', None)
            if gid:
                groups.append({'groupid': gid})
                continue

            # 2) Otherwise, try to resolve by name (e.g., for template-like objects).
            name, _status = ('', False)
            try:
                name, _status = group.render()
            except Exception:
                _status = False

            if _status and name:
                zbx_result = self.api.hostgroup.get(search={'name': name}) or []
                if len(zbx_result) == 1 and 'groupid' in zbx_result[0]:
                    groups.append({'groupid': zbx_result[0]['groupid']})
                elif zbx_result:
                    # If multiple, prefer exact-name match if available
                    match = next((g for g in zbx_result if g.get('name') == name and 'groupid' in g), None)
                    if match:
                        groups.append({'groupid': match['groupid']})
            # If no gid and no resolvable name, skip silently

        return groups

    def get_hostinventory(self):
        hostinventory = self.context.get('all_objects', {}).get('hostinventory', None)
        inventory = {}
        inventory_mode = 0

        if hostinventory:
            inventory_mode = hostinventory.inventory_mode or 0

            for field_name, (rendered_value, success) in hostinventory.render_all_fields().items():
                if success and rendered_value:
                    inventory[field_name] = rendered_value

        result = {'inventory_mode': inventory_mode}
        if inventory:
            result['inventory'] = inventory

        return result

    def verify_maintenancewindow(self):
        status = self.obj.assigned_object.status
        object_type = self.obj.assigned_object._meta.model_name  # "device" or "virtualmachine"
        status_mapping = getattr(self.pluginsettings.statusmapping, object_type, {})
        zabbix_status = status_mapping.get(status)

        object_ct = ContentType.objects.get_for_model(self.obj.assigned_object)
        mw_assignments = ZabbixMaintenanceObjectAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=self.obj.assigned_object.id)

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
            maintenance = ZabbixMaintenance(name=f'[AUTOMATIC] {str(self.obj.assigned_object)}', description='Automatically created maintenance object due to the object status', automatic=True, active_since=now, active_till=end_date, zabbixserver=self.obj.zabbixserver)
            maintenance.save()

            # Assign this host to the Maintenance object
            ZabbixMaintenanceObjectAssignment(zabbixmaintenance=maintenance, assigned_object_type=object_ct, assigned_object_id=self.obj.assigned_object.id).save()
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

    def delete(self):
        if not self.obj.hostid:
            try:
                self.obj.update_sync_info(success=False, message='Host already deleted or missing host ID.')
            except Exception:
                pass
            return

        try:
            # Check for maintenances where this host is attached to
            # If found:
            #    Check if this host is the only host for this maintenance; if so - delete the maintenance window
            #    If not: delete the host from the maintenance window
            object_ct = ContentType.objects.get_for_model(self.obj.assigned_object)
            maintenances = self.api.maintenance.get(hostids=[self.obj.hostid], selectHosts='extend')
            for mw in maintenances:
                # Check per maintenance window if this host is the only host in the window or not. If it is, we can delete it
                # If not, we should delete the host from the Netbox window
                if len(mw['hosts']) > 1:
                    # Filter out the hostid
                    hosts = [{'hostid': host['hostid']} for host in mw['hosts'] if int(host['hostid']) != self.obj.hostid]
                    # Update the maintenance window in Zabbix without our hostid in it
                    self.api.maintenance.update(maintenanceid=mw['maintenanceid'], hosts=hosts)
                    for assignment in ZabbixMaintenanceObjectAssignment.objects.filter(maintenanceid=mw['maintenanceid'], assigned_object_type=object_ct, assigned_object_id=self.obj.assigned_object.id):
                        assignment.delete()  # Delete the Assignment from Netbox;

                # If our host is the only one in the Maintenance Object
                # Delete it...
                else:
                    self.api.maintenance.delete([mw['maintenanceid']])
                    ZabbixMaintenance.objects.get(maintenanceid=mw['maintenanceid']).delete()

            # Delete from Zabbix
            self.api_object().delete([self.obj.hostid])

            try:
                # Unset the host ID and save
                self.obj.hostid = None
                self.obj.save()
            except ValidationError:
                pass

            # Also clear host IDs from related interfaces
            try:
                ZabbixHostInterface.objects.filter(
                    assigned_object_type=self.obj.assigned_object_type,
                    assigned_object_id=self.obj.assigned_object.id,
                    zabbixserver=self.obj.zabbixserver,
                ).update(interfaceid=None)

                self.obj.update_sync_info(success=True, message='Host deleted from Zabbix.')
            except Exception:
                pass

        except Exception as e:
            self.obj.update_sync_info(success=False, message=f'Failed to delete host: {e}')
            raise RuntimeError(f'Failed to delete host {self.obj.hostid} from Zabbix: {e}')

    def verify_hostinterfaces(self):
        # If there is no hostid, no need to continue - so fail early
        if not self.obj.hostid:
            return {}

        # Extract the currently expected interfaces
        expected_hostinterfaces = self.context.get('all_objects', {}).get('hostinterfaces', [])
        expected_ids = {int(expected_hostinterface.interfaceid) for expected_hostinterface in expected_hostinterfaces}

        # Get currently assigned hostinterface from Zabbix
        current_hostinterfaces = self.api.hostinterface.get(output=['extend'], hostids=self.obj.hostid)
        current_ids = {int(current_hostinterface['interfaceid']) for current_hostinterface in current_hostinterfaces}

        to_be_deleted = current_ids - expected_ids
        for id_to_delete in to_be_deleted:
            self.api.hostinterface.delete(id_to_delete)

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
