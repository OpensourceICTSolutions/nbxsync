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
        # Hierarchy appended after device/role/platform (first-seen wins)
        ['device', 'site'],
        ['site'],
        ['site', 'group'],
        ['site', 'region'],
        ['cluster', '_site'],
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
    'trigger_dependencies': {
        'enabled': False,
        'levels': [
            {
                'name': 'access_point',
                'roles': ['access point', 'access-point', 'ap'],
                'trigger_description': 'AP status',
            },
            {
                'name': 'switch',
                'roles': ['switch', 'sw'],
                'trigger_description': 'Switch status',
            },
            {
                'name': 'gateway',
                'roles': [
                    'gateway',
                    'gw',
                    'firewall',
                    'router',
                ],
                'trigger_description': 'Gateway status',
            },
        ],
    },
    'no_alerting_tag': 'NO_ALERTING',
    'no_alerting_tag_value': '1',
    'attach_objtag': True,
    'objtag_type': 'nb_type',
    'objtag_id': 'nb_id',
    'custom_field_hostname':'',
    'custom_field_display_name':'',
    'exclude_tag': '',
}
```

## Inheritance Chain

The `inheritance_chain` setting defines which NetBox objects are traversed when resolving Zabbix assignments. Assignments (templates, tags, hostgroups, macros, proxy/server, interfaces, inventory, configuration groups) made on any object in the chain are inherited by the device or VM being synced, with direct assignments taking priority. Within inherited sources, **first path wins** (leaf-first order as listed).

Host interfaces are the exception: they are defined on a Device/VM directly, on a `ZabbixConfigurationGroup`, or on a NetBox Tag (as a reusable interface template), because an interface needs a per-device endpoint. To apply interfaces to a whole Site, SiteGroup or Region, assign a Configuration Group at that level — its interfaces are then cloned onto every inheriting device with that device's primary IP.

### VirtualMachine and `device`-prefixed paths

Paths that start with `device` (for example `['device']`, `['device', 'role']`, `['device', 'device_type', 'manufacturer']`) describe the associated physical device.

Virtual Device Contexts keep these paths (a VDC is part of its parent device). VirtualMachines skip them: on NetBox 4.3+, `VirtualMachine.device` links a guest to its hosting device, and walking that path would leak host hardware assignments onto the guest. VMs still inherit via cluster, site, role, platform and tag paths that apply to the VM itself.

### Site, SiteGroup, and Region Inheritance

Hierarchy paths are appended after device/role/platform/manufacturer/cluster paths so upgrading into Site inheritance does not silently override existing Role or Platform assignments. SiteGroup and Region ancestors are walked automatically when a group or region is reached.

| Path | Description |
|------|-------------|
| `['device', 'site']` | The device's site (also VDC → device → site; not walked for VirtualMachines) |
| `['site']` | Site (direct) |
| `['site', 'group']` | The site's SiteGroup (parents walked) |
| `['site', 'region']` | The site's region (parents walked) |
| `['cluster', '_site']` | The cluster's scoped site for VMs (`CachedScopeMixin._site`) |

If you previously customized `inheritance_chain` with Site paths ahead of Role/Platform, review hosts that have both a Site-level and a Role/Platform-level assignment — effective winners may change. Prefer appending hierarchy paths.

For example, assigning a `ZabbixServerAssignment` (proxy) to a `SiteGroup` means every device at every site in that SiteGroup inherits the proxy — no per-device assignment needed.

### Tag-based assignments

NetBox Tags are assignment targets: hostgroup, template, tag, macro, server, inventory, configuration group and host interface assignments can be pointed at a Tag. Every Device, VDC or VirtualMachine carrying that tag then inherits the assignment. Direct assignments on the object still take priority. Tag-targeted rows are collected before the `inheritance_chain` paths (first seen wins).

Tagging an object adds the membership on the next sync; removing the tag removes it. The inherited source is shown as `Tag: <name>`. Create Tag-targeted assignments via the API (`assigned_object_type` / `assigned_object_id`); the assignment forms expose Site hierarchy pickers but not a Tag picker.


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

### trigger_dependencies

When enabled, nbxSync updates Zabbix trigger dependencies after a successful device host sync. The feature uses NetBox cabling and ordered dependency levels to build dependency chains such as:

```text
access point trigger -> switch trigger -> gateway/firewall trigger
```

This feature is disabled by default. Enable it only when the configured role tokens match your NetBox device role names or slugs and the configured trigger descriptions match your Zabbix trigger names.

Both pieces are required:

- Role matching decides which dependency level a NetBox device belongs to. Role names and slugs are compared case-insensitively.
- Interface cabling decides which directly connected devices are considered.
- The order of `levels` decides dependency direction. Lower levels depend on directly connected higher levels.

For example, an access point role named `Wireless AP` will not match the defaults unless you add `wireless ap` or the role slug to the access point level's `roles`. A device with a matching role but no connected higher-level neighbor is skipped because nbxSync cannot determine its upstream dependency.

| Key        | Default | Description |
|------------|---------|-------------|
| `enabled`  | `False` | Enable trigger dependency updates after host sync |
| `levels`   | AP, switch, gateway/firewall | Ordered from lowest child to highest parent |
| `name`     | Level-specific | Human-readable level name used for configuration clarity |
| `roles`    | Level-specific role tokens | NetBox device role names/slugs that belong to this level |
| `trigger_description` | Level-specific trigger name | Zabbix trigger description on hosts in this level |

The default levels are ordered as access point, switch, gateway/firewall. With those defaults, a connected access point depends on its connected switch, and a connected switch depends on its connected gateway or firewall. Cable direction does not matter; nbxSync looks at directly connected devices and uses the level order to decide which device is the child and which device is the parent.

To support more device types or vendor-specific role names, add their NetBox role names or slugs to the appropriate level. To support a different hierarchy, add or reorder levels from lowest child to highest parent.

Existing Zabbix dependencies whose descriptions do not match the managed parent trigger descriptions are preserved. Dependencies matching the managed parent trigger descriptions are replaced with the current cabling-derived parent triggers.

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

### custom_field_hostname and custom_field_display_name
You can use these fields to map the connection between NetBox and the Zabbix hostname and display name. The device name is used as the default.

### exclude_tag

When set to a non-empty string (e.g. `'do_not_monitor'`), any `ZabbixTagAssignment` with a tag matching this name — whether assigned directly on a Device/VM or inherited from a Role, Platform, Site, SiteGroup, Region, Manufacturer, or Configuration Group — causes the host to be excluded from Zabbix sync entirely. No Zabbix host is created, and if a host was previously synced it is deleted from Zabbix.

This is useful for excluding device classes that should never be monitored (e.g. desktop PCs, VDI sessions, test lab devices) without removing their Site or Platform assignments.

The tag itself is never pushed to Zabbix — it is only used as a signal during sync resolution and is filtered out before Jinja2 rendering.

Defaults to `''` (empty string = feature disabled).

## Enabling and Disabling Synchronization

Two separate `sync_enabled` flags control whether synchronization to Zabbix is active.

**On `ZabbixServer`**: disabling this stops all synchronization for every host, proxy, maintenance, and template associated with that server. Jobs  will still be enqueued but will exit immediately without making any API calls.

**On `ZabbixServerAssignment`**: disabling this stops synchronization for that specific device/VM assignment only. Other assignments to the same or different Zabbix servers are unaffected.

Both flags must be `True` for a sync to proceed. The "Sync Status" column on the Zabbix Server Assignments list shows a green check only when both the assignment and its server are enabled.
