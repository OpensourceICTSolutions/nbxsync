from typing import Dict, List, Optional, Tuple

from django.apps import apps
from pydantic import BaseModel, Field, field_validator

from nbxsync.choices.syncsot import SyncSOT
from nbxsync.choices.zabbixstatus import ZabbixHostStatus

__all__ = ('PluginSettingsModel',)


class SoTConfig(BaseModel):
    proxygroup: SyncSOT = SyncSOT.NETBOX
    proxy: SyncSOT = SyncSOT.NETBOX
    macro: SyncSOT = SyncSOT.NETBOX
    host: SyncSOT = SyncSOT.NETBOX
    hostmacro: SyncSOT = SyncSOT.NETBOX
    hostgroup: SyncSOT = SyncSOT.NETBOX
    hostinterface: SyncSOT = SyncSOT.NETBOX
    hosttemplate: SyncSOT = SyncSOT.NETBOX
    maintenance: SyncSOT = SyncSOT.NETBOX


class StatusMapping(BaseModel):
    device: Dict[str, ZabbixHostStatus] = Field(default_factory=dict)
    virtualmachine: Dict[str, ZabbixHostStatus] = Field(default_factory=dict)


class SNMPConfig(BaseModel):
    snmp_community: str = Field(default='{$SNMP_COMMUNITY}')
    snmp_authpass: str = Field(default='{$SNMP_AUTHPASS}')
    snmp_privpass: str = Field(default='{$SNMP_PRIVPASS}')

    @field_validator('snmp_community', 'snmp_authpass', 'snmp_privpass', mode='before')
    def validate_macro_format(cls, v: str) -> str:
        if not (isinstance(v, str) and v.startswith('{$') and v.endswith('}')):
            raise ValueError("Value must start with '{$' and end with '}'")
        return v


class BackgroundSyncConfig(BaseModel):
    enabled: bool = Field(default=True)
    interval: int = Field(default=60)


class BackgroundSync(BaseModel):
    objects: BackgroundSyncConfig = Field(default_factory=BackgroundSyncConfig)
    templates: BackgroundSyncConfig = Field(default_factory=BackgroundSyncConfig)
    proxies: BackgroundSyncConfig = Field(default_factory=BackgroundSyncConfig)
    maintenance: BackgroundSyncConfig = Field(default_factory=BackgroundSyncConfig)


class PluginSettingsModel(BaseModel):
    sot: SoTConfig = SoTConfig()
    statusmapping: StatusMapping = Field(default_factory=StatusMapping)
    snmpconfig: SNMPConfig = Field(default_factory=SNMPConfig)
    backgroundsync: BackgroundSync = Field(default_factory=BackgroundSync)
    inheritance_chain: List[Tuple[str, ...]] = Field(
        default_factory=lambda: [
            ('device',),
            ('role',),
            (
                'device',
                'role',
            ),
            (
                'role',
                'parent',
            ),
            (
                'device',
                'role',
                'parent',
            ),
            (
                'device',
                'device_type',
            ),
            ('device_type',),
            (
                'device',
                'platform',
            ),
            ('platform',),
            (
                'device',
                'device_type',
                'manufacturer',
            ),
            (
                'device_type',
                'manufacturer',
            ),
            (
                'device',
                'manufacturer',
            ),
            ('manufacturer',),
            ('cluster',),
            (
                'cluster',
                'type',
            ),
            ('type',),
        ]
    )
    no_alerting_tag: str = Field(default='NO_ALERTING')
    no_alerting_tag_value: str = Field(default='1')
    maintenance_window_duration: int = Field(default=3600)
    attach_objtag: bool = Field(default=True)
    objtag_type: str = Field(default='nb_type')
    objtag_id: str = Field(default='nb_id')


# Helper function
def get_plugin_settings() -> PluginSettingsModel:
    plugin_config = apps.get_app_config('nbxsync')
    return plugin_config.validated_config
