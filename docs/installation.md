# Installation

## Prerequisites

- NetBox >= 4.x
- Python >= 3.8
- Zabbix server >= 7.0

## Steps

### Install the plugin

```bash
cd /opt/netbox/netbox/
source venv/bin/activate
pip install nbxsync
echo nbxsync >> /opt/netbox/local_requirements.txt
```

### Configuration

If you want to change the default configuration, can add the following configuration and alter it accordingly. This is _not_ required though.

```python title="netbox/configuration.py"
PLUGINS = ['nbxsync']
PLUGINS_CONFIG = {
    "nbxsync": {
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
            ['role'],
            ['role', 'parent'],
            ['device_type'],
            ['platform'],
            ['device_type', 'manufacturer'],
            ['manufacturer'],
            ['cluster'],
            ['cluster', 'type'],
            ['type'],
        ],
        'backgroundsync': {
            'objects': {
                'enabled': True,
                'interval': 60, # 1 hour
            },
            'templates': {
                'enabled': True,
                'interval': 1440, # 24 hours
            },
            'proxies': {
                'enabled': True,
                'interval': 1440, # 24 hours
            },
            'maintenance': {
                'enabled': True,
                'interval': 15, # 15 minutes
            },
        },
        'no_alerting_tag': 'NO_ALERTING',
    }
```

### Run migrations

```python
python3 manage.py migrate nbxsync
python3 manage.py collectstatic --no-input
```

### Restart services

```bash
sudo systemctl restart netbox netbox-worker
```
