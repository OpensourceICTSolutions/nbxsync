from email.utils import parseaddr
from importlib import import_module
from importlib.metadata import metadata

from django.conf import settings as django_settings
from pydantic import ValidationError

from netbox.plugins import PluginConfig

from .settings import PluginSettingsModel

metadata = metadata('nbxsync')


author_headers = metadata.get_all('Author') or metadata.get_all('Maintainer') or []

# Pick the first header with a valid email, else fallback to the first header, else defaults.
name, email = None, None
for hdr in author_headers:
    n, e = parseaddr(hdr or '')
    if e:
        name, email = n or None, e
        break
if name is None and author_headers:
    # No email found; at least keep the name part if present
    name = parseaddr(author_headers[0] or '')[0] or author_headers[0]

# Sensible defaults if nothing is present
name = name or 'nbxSync'
email = email or 'info@oicts.com'


class NetboxZabbix(PluginConfig):
    name = metadata.get('Name').replace('-', '_')
    verbose_name = metadata.get('Summary')
    description = 'Zabbix'
    version = metadata.get('Version')
    author = name
    author_email = email
    base_url = 'nbxsync'
    min_version = '4.1.0'
    required_settings = []
    default_settings = {
        'sot': {
            'proxygroup': 'netbox',
            'proxy': 'zabbix',
            'macro': 'netbox',
            'host': 'netbox',
            'hostmacro': 'netbox',
            'hostgroup': 'netbox',
            'hostinterface': 'netbox',
            'hosttemplate': 'netbox',
            'maintenance': 'netbox',
        },
        'statusmapping': {
            'device': {
                'active': 'enabled',
                'planned': 'disabled',
                'failed': 'deleted',
                'staged': 'disabled',
                'offline': 'deleted',
                'inventory': 'deleted',
                'decommissioning': 'deleted',
            },
            'virtualmachine': {
                'offline': 'deleted',
                'active': 'enabled',
                'planned': 'enabled_in_maintenance',
                'paused': 'enabled_no_alerting',
                'failed': 'deleted',
            },
        },
        'snmpconfig': {
            'snmp_community': '{$SNMP_COMMUNITY}',
            'snmp_authpass': '{$SNMP_AUTHPASS}',
            'snmp_privpass': '{$SNMP_PRIVPASS}',
        },
        'inheritance_chain': [
            ['device'],
            ['role'],
            ['device', 'role'],
            ['role', 'parent'],
            ['device', 'role', 'parent'],
            ['device', 'device_type'],
            ['device_type'],
            ['device', 'platform'],
            ['platform'],
            ['device', 'device_type', 'manufacturer'],
            ['device_type', 'manufacturer'],
            ['device', 'manufacturer'],
            ['manufacturer'],
            ['cluster'],
            ['cluster', 'type'],
            ['type'],
        ],
        'backgroundsync': {
            'objects': {
                'enabled': True,
                'interval': 60,  # 1 hour
            },
            'templates': {
                'enabled': True,
                'interval': 1440,  # 24 hours
            },
            'proxies': {
                'enabled': True,
                'interval': 1440,  # 24 hours
            },
            'maintenance': {
                'enabled': True,
                'interval': 15,  # 15 minutes
            },
        },
        'no_alerting_tag': 'NO_ALERTING',
        'no_alerting_tag_value': '1',
        'maintenance_window_duration': 3600,
    }
    queues = []
    validated_config = None
    django_apps = []

    def ready(self):
        super().ready()

        # Settings setup
        raw_config = django_settings.PLUGINS_CONFIG.get(self.name, {})
        try:
            self.validated_config = PluginSettingsModel(**raw_config)
        except ValidationError as e:
            raise RuntimeError(f'Invalid plugin configuration for {self.name}: {e}')

        # Import signals
        import nbxsync.signals  # noqa: F401

        # If automatic sync for the Objects (Device/VM) is enabled, import the job
        if self.validated_config.backgroundsync.objects.enabled:
            from nbxsync.systemjobs.sync_objects import SyncObjectsJob  # noqa: F401

        # If automatic sync for the Templates is enabled, import the job
        if self.validated_config.backgroundsync.templates.enabled:
            from nbxsync.systemjobs.sync_templates import SyncTemplatesJob  # noqa: F401

        # If automatic sync for the Proxies is enabled, import the job
        if self.validated_config.backgroundsync.proxies.enabled:
            from nbxsync.systemjobs.sync_proxies import SyncProxiesJob  # noqa: F401

        # If automatic sync for the Maintenance is enabled, import the job
        if self.validated_config.backgroundsync.maintenance.enabled:
            from nbxsync.systemjobs.sync_maintenance import SyncMaintenanceJob  # noqa: F401


config = NetboxZabbix
