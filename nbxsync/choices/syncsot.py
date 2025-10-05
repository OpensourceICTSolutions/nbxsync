from enum import Enum


class SyncSOT(str, Enum):
    ZABBIX = 'zabbix'
    NETBOX = 'netbox'
