# Configuration

The plugin is configuration to do exactly what you want, by means of the plugin settings. As described in the [installation instructions](installation.md)), the default configuration is as follows:

```python
"nbxsync": {
    'sot': {
        'proxygroup': 'netbox',
        'proxy': 'netbox',
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
    'attach_objtag': True,
    'objtag_type': 'nb_type',
    'objtag_id': 'nb_id'
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

### backgroundsync

If wanted, system jobs can be used to automatically sync objects

#### objects

This key is used to determine if 'objects' (that is: Devices and/or Virtual Machines) are to be automatically synched to/from Zabbix

##### enabled

Either true or false (default: True)

##### interval

Used to determine the interval to sync Devices and Virtual Machines to/from Zabbix, in minutes (default: 60)

#### templates

Controls automatic synchronization of Zabbix Templates into NetBox (the same
operation triggered by the `Sync Templates` button on a Zabbix Server).

- **enabled**: Either `True` or `False` (default: `True`)
- **interval**: Interval in minutes between runs (default: `1440` — 24 hours)

This runs as the `Zabbix Sync Templates job` system job. It imports templates
and their macros, computes interface requirements from item types, and removes
orphaned template records that no longer exist in Zabbix.

#### proxies

Controls automatic synchronization of Zabbix Proxies from NetBox to Zabbix.

- **enabled**: Either `True` or `False` (default: `True`)
- **interval**: Interval in minutes between runs (default: `1440` — 24 hours)

This runs as the `Zabbix Sync Proxies job` system job.

#### maintenance

Controls automatic synchronization of Zabbix Maintenance windows from NetBox
to Zabbix.

- **enabled**: Either `True` or `False` (default: `True`)
- **interval**: Interval in minutes between runs (default: `15` — 15 minutes)

This runs as the `Zabbix Sync Maintenance job` system job. Only maintenance
windows that have at least one period and one object assignment are included.
See [Zabbix Maintenance](zabbixmaintenance.md) for details.

### no_alerting_tag

This defines the tag to be set when a host has the 'enabled_no_alerting' status. Use just a string value with no ${ } around the tag. Defaults to 'NO_ALERTING'.

### no_alerting_tag_value

Defines the value to be set to the no_alerting_tag. Defaults to '1'

### maintenance_window_duration

This sets the value of the duration of the maintenance window that is automatically created when a host has the status 'enabled_in_maintenance'
Is defined in seconds; defaults to 3600 (1 hour)

### snmpconfig

Controls which Zabbix host macro names are used to push SNMP credentials
onto hosts. When a `ZabbixHostInterface` of type SNMP has `snmp_pushcommunity`  enabled, nbxSync automatically creates host macros on the Zabbix host carrying  the SNMP community string or SNMPv3 passphrases.

| Key              | Default             | Description                                         |
|------------------|---------------------|-----------------------------------------------------|
| `snmp_community` | `{$SNMP_COMMUNITY}` | Macro name for the SNMPv1/v2 community string       |
| `snmp_authpass`  | `{$SNMP_AUTHPASS}`  | Macro name for the SNMPv3 authentication passphrase |
| `snmp_privpass`  | `{$SNMP_PRIVPASS}`  | Macro name for the SNMPv3 privacy passphrase        |

All three values must be valid Zabbix user macro names (i.e. starting with `{$` and ending with `}`).

If you also define a `ZabbixMacroAssignment` with the same macro name on a  device, the manually defined value takes precedence over the SNMP-derived one.

### attach_objtag

When `True` (the default), nbxSync automatically pushes two tags onto every Zabbix host it syncs:

- A tag named by `objtag_type` containing the NetBox object type (e.g. `device`, `virtualmachine`, `virtualdevicecontext`).
- A tag named by `objtag_id` containing the NetBox object's database ID.

These tags allow you to navigate from a Zabbix host back to the corresponding  NetBox record, and can be used in Zabbix actions or maintenance tag selectors.

| Key             | Default   | Description                         |
|-----------------|-----------|-------------------------------------|
| `attach_objtag` | `True`    | Enable or disable auto-tagging      |
| `objtag_type`   | `nb_type` | Tag name for the NetBox object type |
| `objtag_id`     | `nb_id`   | Tag name for the NetBox object ID   |

## Enabling and Disabling Synchronization

Two separate `sync_enabled` flags control whether synchronization to Zabbix is active.

**On `ZabbixServer`**: disabling this stops all synchronization for every host, proxy, maintenance, and template associated with that server. Jobs  will still be enqueued but will exit immediately without making any API calls.

**On `ZabbixServerAssignment`**: disabling this stops synchronization for that specific device/VM assignment only. Other assignments to the same or different Zabbix servers are unaffected.

Both flags must be `True` for a sync to proceed. The "Sync Status" column on the Zabbix Server Assignments list shows a green check only when both the assignment and its server are enabled.