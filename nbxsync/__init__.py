from email.utils import parseaddr
from importlib.metadata import metadata

from django.conf import settings as django_settings

from netbox.plugins import PluginConfig
from pydantic import ValidationError

from nbxsync.settings import PluginSettingsModel

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
name = name or 'nbxsync'
email = email or 'info@oicts.com'


class nbxSync(PluginConfig):
    name = metadata.get('Name').replace('-', '_')
    verbose_name = metadata.get('Summary')
    description = 'Zabbix'
    version = metadata.get('Version')
    author = name
    author_email = email
    base_url = 'nbxsync'
    min_version = '4.2.4'
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
        'attach_objtag': False,
        'objtag_type': 'nb_type',
        'objtag_id': 'nb_id',
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

        # Dynamically attach reverse relation to all allowed target models for a
        # ZabbixConfigurationGroup Assignment — without hitting the DB in ready()
        try:
            from django.apps import apps
            from django.contrib.contenttypes.fields import GenericRelation
            from django.db.models import Q

            configurationgroupassignment = apps.get_model(self.name, 'ZabbixConfigurationGroupAssignment')
            limit_q: Q = configurationgroupassignment._meta.get_field('assigned_object_type')._limit_choices_to

            # Evaluate a (simple) Q tree on a model using only app_label/model_name,
            # supporting AND/OR, negation, exact and __in on those two fields.
            def q_matches_model(q, model):
                def eval_node(node):
                    # Start with neutral element for connector
                    result = None
                    for child in node.children:
                        if isinstance(child, Q):
                            val = eval_node(child)
                        else:
                            key, value = child
                            app_label = model._meta.app_label
                            model_name = model._meta.model_name

                            if key in ('app_label', 'app_label__exact'):
                                val = app_label == value
                            elif key == 'app_label__in':
                                val = app_label in value
                            elif key in ('model', 'model__exact'):
                                val = model_name == value
                            elif key == 'model__in':
                                val = model_name in value
                            else:
                                # Unknown clause — treat as "don't care" True
                                val = True

                        if result is None:
                            result = val
                        else:
                            result = (result and val) if node.connector == 'AND' else (result or val)

                    result = True if result is None else result
                    return not result if node.negated else result

                return eval_node(q)

            def make_gr():
                return GenericRelation(
                    configurationgroupassignment,
                    content_type_field='assigned_object_type',
                    object_id_field='assigned_object_id',
                    related_query_name='zabbix_assignment',
                )

            # Iterate all registered models (app registry), filter with Q, and attach.
            for model in apps.get_models():
                # Skip if this model doesn't match the limit_q
                if limit_q and not q_matches_model(limit_q, model):
                    continue

                # Avoid double-adds on autoreload
                if not hasattr(model, 'zabbixconfigurationgroupassignment'):
                    model.add_to_class('zabbixconfigurationgroupassignment', make_gr())

                # Convenience property when you typically have ≤1 assignment
                if not hasattr(model, 'zabbixconfigurationgroup'):

                    def _zabbixconfigurationgroup(self_obj):
                        mgr = getattr(self_obj, 'zabbixconfigurationgroupassignment', None)
                        if not mgr:
                            return None
                        assn = mgr.first()
                        return assn.zabbixconfigurationgroup if assn else None

                    model.add_to_class('zabbixconfigurationgroup', property(_zabbixconfigurationgroup))

        except Exception:
            pass


config = nbxSync
