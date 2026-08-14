from ipam.models import IPAddress
from nbxsync.models import ZabbixServerAssignment

from .syncbase import ZabbixSyncBase


class HostInterfaceSync(ZabbixSyncBase):
    id_field = 'interfaceid'
    sot_key = 'hostinterface'

    def api_object(self):
        return self.api.hostinterface

    def get_name_value(self):
        return self.obj.assigned_object.name

    def find_by_name(self):
        hostid = self.context.get('hostid', None)
        if not hostid:
            return []
        return self.api_object().get(hostids=[hostid], filter={'type': str(self.obj.type)})

    def get_create_params(self):
        hostid = self.context.get('hostid', None)
        zbxserverassignment = None

        if not hostid:
            # No HostID, get it from the assignment
            zbxserverassignment = ZabbixServerAssignment.objects.filter(assigned_object_type=self.obj.assigned_object_type, assigned_object_id=self.obj.assigned_object.id).first()
            # If the assignment isnt found... Return
            if not zbxserverassignment:
                return {}

            # Update the hostid field :)
            hostid = zbxserverassignment.hostid

        ipaddr = ''
        if self.obj.ip_id:
            ipaddr = IPAddress.objects.get(id=self.obj.ip_id).address.ip
        elif self.context.get('_instance'):
            # If the interface is inherited (e.g. from SiteGroup or Role)
            # and has no IP assigned, fall back to the device's primary IP
            instance = self.context.get('_instance')
            primary_ip = getattr(instance, 'primary_ip4', None) or getattr(instance, 'primary_ip6', None)
            if primary_ip:
                ipaddr = primary_ip.address.ip

        dns_name, _ = self.obj.render_dns()
        result = {
            'hostid': hostid,
            'type': self.obj.type,
            'ip': str(ipaddr),
            'dns': dns_name,
            'port': str(self.obj.port),
            'useip': self.obj.useip,
            'main': self.obj.interface_type,
        }

        if self.obj.type == 2:  # SNMP
            snmp_dict = {
                'version': self.obj.snmp_version,
                'bulk': 1 if self.obj.snmp_usebulk else 0,
            }

            if self.obj.snmp_version in [1, 2]:  # community is required if the SNMP Version is SNMPv1 or SNMPv2
                snmp_community_macro = getattr(self.pluginsettings.snmpconfig, 'snmp_community', '{$SNMP_COMMUNITY}')
                snmp_dict['community'] = snmp_community_macro

            if self.obj.snmp_version in [2, 3]:
                snmp_dict['max_repetitions'] = self.obj.snmp_max_repetitions

            if self.obj.snmp_version == 3:
                snmp_authpass_macro = getattr(self.pluginsettings.snmpconfig, 'snmp_authpass', '{$SNMPV3_AUTHPASS}')
                snmp_privpass_macro = getattr(self.pluginsettings.snmpconfig, 'snmp_privpass', '{$SNMPV3_PRIVPASS}')

                snmp_dict['contextname'] = self.obj.snmpv3_context_name
                snmp_dict['securityname'] = self.obj.snmpv3_security_name
                snmp_dict['securitylevel'] = self.obj.snmpv3_security_level
                snmp_dict['authprotocol'] = self.obj.snmpv3_authentication_protocol
                snmp_dict['privprotocol'] = self.obj.snmpv3_privacy_protocol

                if self.obj.snmp_pushcommunity:
                    snmp_dict['authpassphrase'] = snmp_authpass_macro
                    snmp_dict['privpassphrase'] = snmp_privpass_macro

            result['details'] = snmp_dict

        return result

    def get_update_params(self, **kwargs):
        params = self.get_create_params()
        params['interfaceid'] = self.obj.interfaceid

        # Zabbix forbids changing hostid on update
        params.pop('hostid', None)
        return params

    def result_key(self):
        return 'interfaceids'

    def sync_from_zabbix(self, data):
        try:
            self.obj.interfaceid = int(data['interfaceid'])
            self.obj.type = int(data.get('type', self.obj.type))
            self.obj.useip = int(data.get('useip', self.obj.useip))
            self.obj.interface_type = int(data.get('main', self.obj.interface_type))  # 'main' indicates default interface
            self.obj.dns = data.get('dns', '')
            self.obj.port = int(data.get('port')) if data.get('port') else None

            ip = data.get('ip')
            if ip:
                from ipam.models import IPAddress

                ip_obj = IPAddress.objects.filter(address__net_host=ip).first()
                self.obj.ip = ip_obj

            # SNMP handling
            snmp_data = data.get('details', {})
            if self.obj.type == 2:  # SNMP
                self.obj.snmp_version = snmp_data.get('version', self.obj.snmp_version)
                self.obj.snmp_usebulk = snmp_data.get('bulk', 1) == 1

                if self.obj.snmp_version in [1, 2]:
                    self.obj.snmp_community = snmp_data.get('community', '')

                if self.obj.snmp_version in [2, 3]:
                    self.obj.snmp_max_repetitions = int(data.get('max_repetitions', 10))

                if self.obj.snmp_version == 3:
                    self.obj.snmpv3_context_name = snmp_data.get('context_name', '')
                    self.obj.snmpv3_security_name = snmp_data.get('security_name', '')
                    self.obj.snmpv3_security_level = snmp_data.get('securitylevel')
                    self.obj.snmpv3_authentication_protocol = snmp_data.get('authprotocol')
                    self.obj.snmpv3_privacy_protocol = snmp_data.get('privprotocol')

                    # Optional passphrases are Zabbix macros, don't overwrite them unless required
                    # self.obj.snmpv3_authentication_passphrase = snmp_data.get('authpassphrase', '')
                    # self.obj.snmpv3_privacy_passphrase = snmp_data.get('privpassphrase', '')

            self.obj.save()
            self.obj.update_sync_info(success=True, message='')

        except Exception as err:
            self.obj.update_sync_info(success=False, message=str(err))

    def find_by_id(self):
        if not self.obj.interfaceid:
            return []

        found = self.api_object().get(interfaceids=self.obj.interfaceid, output=['interfaceid', 'hostid'])

        if not found:
            # interfaceid no longer exists in Zabbix, clear it so the next sync cycle falls through to find_by_name / try_create
            self.obj.interfaceid = None
            self.obj.save(update_fields=['interfaceid'])
            return []

        expected_hostid = str(self.context.get('hostid') or '')
        if expected_hostid and str(found[0]['hostid']) != expected_hostid:
            # interfaceid exists but belongs to a different host: this is a stale reference.
            # Clear it and let the sync re-establish the correct interface
            self.obj.interfaceid = None
            self.obj.save(update_fields=['interfaceid'])
            return []

        return found
