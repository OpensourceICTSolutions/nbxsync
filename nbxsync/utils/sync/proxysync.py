from nbxsync.choices import ZabbixProxyTypeChoices, ZabbixTLSChoices
from nbxsync.models import ZabbixProxyGroup

from .syncbase import ZabbixSyncBase


class ProxySync(ZabbixSyncBase):
    id_field = 'proxyid'
    sot_key = 'proxy'

    def api_object(self):
        return self.api.proxy

    def result_key(self):
        return 'proxyids'

    def get_create_params(self):
        create_params = {
            'name': self.obj.name,
            'description': self.obj.description,
            'operating_mode': self.obj.operating_mode,
            'custom_timeouts': int(self.obj.custom_timeouts),
            'proxy_groupid': 0,
        }

        if self.obj.proxygroup:
            create_params['proxy_groupid'] = self.obj.proxygroup.proxy_groupid

        if self.obj.operating_mode == ZabbixProxyTypeChoices.ACTIVE:
            if create_params['proxy_groupid'] != 0:
                create_params['local_address'] = self.obj.local_address
                create_params['local_port'] = self.obj.local_port
            create_params['allowed_addresses'] = ','.join(self.obj.allowed_addresses)

            create_params['tls_accept'] = 0
            for x in self.obj.tls_accept:
                # Bitwise OR, not just sum().
                create_params['tls_accept'] |= x

            if ZabbixTLSChoices.PSK in self.obj.tls_accept:
                create_params['tls_psk_identity'] = self.obj.tls_psk_identity
                create_params['tls_psk'] = self.obj.tls_psk

            if ZabbixTLSChoices.CERT in self.obj.tls_accept:
                create_params['tls_issuer'] = self.obj.tls_issuer
                create_params['tls_subject'] = self.obj.tls_subject

        if self.obj.operating_mode == ZabbixProxyTypeChoices.PASSIVE:
            create_params['address'] = self.obj.address
            create_params['port'] = self.obj.port
            create_params['tls_connect'] = self.obj.tls_connect

            if ZabbixTLSChoices.PSK == self.obj.tls_connect:
                create_params['tls_psk_identity'] = self.obj.tls_psk_identity
                create_params['tls_psk'] = self.obj.tls_psk

            if ZabbixTLSChoices.CERT == self.obj.tls_connect:
                create_params['tls_issuer'] = self.obj.tls_issuer
                create_params['tls_subject'] = self.obj.tls_subject

        if self.obj.custom_timeouts:
            create_params['timeout_zabbix_agent'] = self.obj.timeout_zabbix_agent
            create_params['timeout_zabbix_agent'] = self.obj.timeout_zabbix_agent
            create_params['timeout_simple_check'] = self.obj.timeout_simple_check
            create_params['timeout_snmp_agent'] = self.obj.timeout_snmp_agent
            create_params['timeout_external_check'] = self.obj.timeout_external_check
            create_params['timeout_db_monitor'] = self.obj.timeout_db_monitor
            create_params['timeout_http_agent'] = self.obj.timeout_http_agent
            create_params['timeout_ssh_agent'] = self.obj.timeout_ssh_agent
            create_params['timeout_telnet_agent'] = self.obj.timeout_telnet_agent
            create_params['timeout_script'] = self.obj.timeout_script
            create_params['timeout_browser'] = self.obj.timeout_browser

        return create_params

    def get_update_params(self, **kwargs):
        params = self.get_create_params()
        params['proxyid'] = self.obj.proxyid
        return params

    def decode_bitmask(self, value, flags=(1, 2, 4)):
        return [flag for flag in flags if value & flag]

    def sync_from_zabbix(self, data):
        tls_accept = [1]  # Default to 'No Encryption'
        if data.get('tls_accept', 1):
            flags = (1, 2, 4)
            value = int(data.get('tls_acept', 1))
            tls_accept = [flag for flag in flags if value & flag]

        self.obj.proxyid = data.get('proxyid')
        self.obj.name = data.get('name', self.obj.name)
        self.obj.description = data.get('description', '')
        self.obj.operating_mode = int(data.get('operating_mode', self.obj.operating_mode))
        self.obj.tls_connect = data.get('tls_connect', self.obj.tls_connect)

        self.obj.tls_accept = tls_accept
        self.obj.tls_issuer = data.get('tls_issuer', '')
        self.obj.tls_subject = data.get('tls_subject', '')
        self.obj.tls_psk_identity = data.get('tls_psk_identity', '')

        # # Do not sync tls_psk back — write-only

        self.obj.custom_timeouts = bool(int(data.get('custom_timeouts', 0)))
        self.obj.timeout_zabbix_agent = data.get('timeout_zabbix_agent', '')
        self.obj.timeout_simple_check = data.get('timeout_simple_check', '')
        self.obj.timeout_snmp_agent = data.get('timeout_snmp_agent', '')
        self.obj.timeout_external_check = data.get('timeout_external_check', '')
        self.obj.timeout_db_monitor = data.get('timeout_db_monitor', '')
        self.obj.timeout_http_agent = data.get('timeout_http_agent', '')
        self.obj.timeout_ssh_agent = data.get('timeout_ssh_agent', '')
        self.obj.timeout_telnet_agent = data.get('timeout_telnet_agent', '')
        self.obj.timeout_script = data.get('timeout_script', '')
        self.obj.timeout_browser = data.get('timeout_browser', '')

        # If ProxyGroup is set, set it
        if int(data.get('proxy_groupid')) != 0:
            try:
                proxygroup = ZabbixProxyGroup.objects.get(proxy_groupid=int(data.get('proxy_groupid')), zabbixserver=self.obj.zabbixserver.id)
                self.obj.proxygroup = proxygroup
            except ZabbixProxyGroup.DoesNotExist:
                self.obj.proxygroup = None
        else:  # No proxygoup, unset it
            self.obj.proxygroup = None

        self.obj.address = data.get('address', '')
        self.obj.port = data.get('port', '')
        self.obj.local_address = data.get('local_address')
        self.obj.local_port = int(data.get('local_port') or 10051)
        self.obj.allowed_addresses = [address.strip() for address in data.get('allowed_addresses', '').split(',') if address]

        try:
            self.obj.save()
            self.obj.update_sync_info(success=True, message='')
        except Exception as _err:
            self.obj.update_sync_info(success=False, message=str(_err))
