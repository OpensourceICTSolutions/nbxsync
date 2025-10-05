from zabbix_utils import ZabbixAPI


class ZabbixConnection:
    def __init__(self, zabbixserver):
        self.zabbixserver = zabbixserver

        self._ZABBIX_AUTH = {'url': zabbixserver.url, 'validate_certs': zabbixserver.validate_certs}
        self.api = ZabbixAPI(**self._ZABBIX_AUTH)

    def __enter__(self):
        # Attempt login
        try:
            self.api.login(token=self.zabbixserver.token)
        except Exception as e:
            raise ConnectionError(f'Failed to login to Zabbix: {e}')
        return self.api

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.api.logout()
        except Exception:
            pass  # Don't raise error on logout
