from typing import Dict, List, Tuple

from django.apps import apps
from pydantic import BaseModel, Field, field_validator, model_validator

from nbxsync.choices.syncsot import SyncSOT
from nbxsync.choices.zabbixstatus import ZabbixHostStatus

__all__ = ('PluginSettingsModel', 'TriggerDependencyConfig', 'TriggerDependencyLevelConfig')


def _normalize_role_tokens(values):
    """Normalize role tokens using the same semantics as dependency matching."""
    tokens = set()

    for value in values:
        normalized = value.strip().lower()
        tokens.add(normalized)
        tokens.add(normalized.replace('-', ' '))

    return tokens


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
    interval: int = Field(default=360)


class BackgroundSync(BaseModel):
    objects: BackgroundSyncConfig = Field(default_factory=BackgroundSyncConfig)
    templates: BackgroundSyncConfig = Field(default_factory=BackgroundSyncConfig)
    proxies: BackgroundSyncConfig = Field(default_factory=BackgroundSyncConfig)
    maintenance: BackgroundSyncConfig = Field(default_factory=BackgroundSyncConfig)


class TriggerDependencyLevelConfig(BaseModel):
    name: str
    roles: List[str]
    trigger_description: str

    @field_validator('name', 'trigger_description', mode='before')
    def validate_non_empty_string(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError('Value must be a non-empty string')
        return v.strip()

    @field_validator('roles', mode='before')
    def validate_role_tokens(cls, v):
        if not isinstance(v, list) or not v:
            raise ValueError('Role tokens must be a non-empty list')

        cleaned = []
        for role in v:
            if not isinstance(role, str) or not role.strip():
                raise ValueError('Role tokens must be non-empty strings')
            cleaned.append(role.strip())

        return cleaned


class TriggerDependencyConfig(BaseModel):
    # TODO: Move trigger dependency levels to Django models so operators can
    # manage roles and trigger descriptions through the UI/API without restart.
    enabled: bool = Field(default=False)
    levels: List[TriggerDependencyLevelConfig] = Field(
        default_factory=lambda: [
            TriggerDependencyLevelConfig(name='access_point', roles=['access point', 'access-point', 'ap'], trigger_description='AP status'),
            TriggerDependencyLevelConfig(name='switch', roles=['switch', 'sw'], trigger_description='Switch status'),
            TriggerDependencyLevelConfig(name='gateway', roles=['gateway', 'gw', 'firewall', 'router'], trigger_description='Gateway status'),
        ]
    )

    @field_validator('levels', mode='before')
    def validate_levels(cls, v):
        if not isinstance(v, list) or not v:
            raise ValueError('Dependency levels must be a non-empty list')
        return v

    @model_validator(mode='after')
    def validate_unique_levels(self):
        descriptions = {}
        roles = {}

        for level in self.levels:
            previous_level = descriptions.get(level.trigger_description)
            if previous_level is not None:
                raise ValueError(f'Trigger description {level.trigger_description!r} is used by both dependency levels {previous_level!r} and {level.name!r}')

            descriptions[level.trigger_description] = level.name

            for role in _normalize_role_tokens(level.roles):
                previous_level = roles.get(role)
                if previous_level is not None:
                    raise ValueError(f'Role token {role!r} overlaps between dependency levels {previous_level!r} and {level.name!r}')

                roles[role] = level.name

        return self


class PluginSettingsModel(BaseModel):
    sot: SoTConfig = SoTConfig()
    statusmapping: StatusMapping = Field(default_factory=StatusMapping)
    snmpconfig: SNMPConfig = Field(default_factory=SNMPConfig)
    backgroundsync: BackgroundSync = Field(default_factory=BackgroundSync)
    trigger_dependencies: TriggerDependencyConfig = Field(default_factory=TriggerDependencyConfig)
    inheritance_chain: List[Tuple[str, ...]] = Field(
        # Leaf-first. Existing role/platform paths stay ahead of Site hierarchy so
        # adding Site/SiteGroup/Region inheritance does not override Role/Platform
        # assignments on upgrade. Cluster site uses CachedScopeMixin._site (NetBox ≥4.2).
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
            # Hierarchy targets for zero-touch (appended after device/role/platform)
            (
                'device',
                'site',
            ),  # VirtualDeviceContext → device → site
            ('site',),
            (
                'site',
                'group',
            ),
            (
                'site',
                'region',
            ),
            (
                'cluster',
                '_site',
            ),  # NetBox ≥4.2 Cluster scope cache (not .site)
        ]
    )
    no_alerting_tag: str = Field(default='NO_ALERTING')
    no_alerting_tag_value: str = Field(default='1')
    maintenance_window_duration: int = Field(default=3600)
    attach_objtag: bool = Field(default=True)
    objtag_type: str = Field(default='nb_type')
    objtag_id: str = Field(default='nb_id')

    custom_field_hostname: str = Field(default='')
    custom_field_display_name: str = Field(default='')

    # Tag name that, when assigned (inherited or direct) to a Device/VM,
    # excludes the host from Zabbix sync entirely. Uses the same inheritance
    # chain as templates, hostgroups, and other tag assignments.
    exclude_tag: str = Field(default='')

    # Deleting a host in Zabbix destroys its history, so inheritance-driven
    # deletions from lost server assignments are opt-in. While disabled,
    # nbxsync logs the hosts it would have deleted when their assignment
    # disappeared and leaves them untouched, which lets operators review the
    # impact of e.g. a moved Site before any data is lost. Explicit operator
    # decisions (exclude tags, status mapped to deleted, NetBox deletion)
    # always delete.
    allow_inherited_deletion: bool = Field(default=False)

    # Bind to a pre-existing Zabbix host that carries matching nb_type/nb_id
    # tags instead of failing. Off by default: adopting a host that nbxsync did
    # not create means NetBox immediately starts overwriting its configuration.
    adopt_existing_hosts: bool = Field(default=False)


# Helper function
def get_plugin_settings() -> PluginSettingsModel:
    plugin_config = apps.get_app_config('nbxsync')
    return plugin_config.validated_config
