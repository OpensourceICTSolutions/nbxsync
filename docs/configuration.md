# Configuration

The plugin is configuration to do exactly what you want, by means of the plugin settings. As described in the [installation instructions](installation.md)), the default configuration is as follows:

```python
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
    'no_alerting_tag_value': '1',
}
```

## Configuration values

### Source of Truth

The `sot` key determines which system is the Source of Truth: `netbox` or `zabbix`. And as such, which way the sync works. If the SoT is Netbox, data will be synschronized from Netbox to Zabbix. If the SoT is Zabbix, data is synchronized from Zabbix to Netbox - if and where possible (Zabbix doesn't expose all information).

### Statusmapping

The `statusmapping` key influences how certain statusses are interpreted and used. The two models that are to be synchronized are Devices and Virtual Machines. Each of these can be configurated independently of eachother for maximum flexibility.

The key is the `netbox` status whilst the value is the action to be taken in Zabbix.

### Actions

#### enabled

This status results in the host to be enabled in Zabbix

#### disabled

This status results in the host to be disabled in Zabbix

#### deleted

This status results in the host to be deleted from Zabbix

#### enabled_in_maintenance

If a host has this status, it is enabled in Zabbix, but a maintenance period will be configured with this device.

#### enabled_no_alerting

If a host has this status, it is enabled in Zabbix, but it will have a tag with the value "1" appended. By default this tag will be set to 'NO_ALERTING', but this is configurable using the `no_alerting_tag` configuration. This allows for configuration in Zabbix to disable alerting (see [https://www.zabbix.com/documentation/current/en/manual/config/notifications/action])

### background_sync

If wanted, system jobs can be used to automatically sync objects

#### objects

This key is used to determine if 'objects' (that is: Devices and/or Virtual Machines) are to be automatically synched to/from Zabbix

##### enabled

Either true or false (default: True)

##### interval

Used to determine the interval to sync Devices and Virtual Machines to/from Zabbix, in minutes (default: 60)

### no_alerting_tag

This defines the tag to be set when a host has the 'enabled_no_alerting' status. Use just a string value with no ${ } around the tag. Defaults to 'NO_ALERTING'.

### no_alerting_tag_value

Defines the value to be set to the no_alerting_tag. Defaults to '1'

### maintenance_window_duration

This sets the value of the duration of the maintenance window that is automatically created when a host has the status 'enabled_in_maintenance'
Is defined in seconds; defaults to 3600 (1 hour)
