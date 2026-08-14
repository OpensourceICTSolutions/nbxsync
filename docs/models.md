# Models & Objects

This plugin defines a set of Django models to represent and synchronize NetBox objects with their counterparts in Zabbix.

---

## Core Models

### `ZabbixServer`

This model represents the Zabbix Server where objects are synced from / to.

| Field                | Type         | Description                                                       |
|----------------------|--------------|-------------------------------------------------------------------|
| `name`               | CharField    | Friendly name of the server                                       |
| `description`        | CharField    | Optional description                                              |
| `url`                | URLField     | Full API endpoint URL                                             |
| `token`              | CharField    | API token for authentication                                      |
| `validate_certs`     | BooleanField | Toggle SSL cert validation                                        |
| `sync_enabled`       | BooleanField | Determines if automatic synchronisation from/to Zabbix is enabled |
| `skip_version_check` | BooleanField | Enable/Disable the version check in the Zabbix Utils module       |

Used as the anchor for all synced objects (hosts, templates, etc.).

---

### `ZabbixTemplate`

Maps a template defined in Zabbix.

| Field                    | Type         | Description                              |
|--------------------------|--------------|------------------------------------------|
| `name`                   | CharField    | Template name                            |
| `templateid`             | IntegerField | ID in Zabbix                             |
| `zabbixserver`           | ForeignKey   | Associated `ZabbixServer`                |
| `interface_requirements` | ArrayField   | Required interface types for application |

---

### `ZabbixTemplateAssignment`

Assigns a template to a NetBox object (device, VM, etc.).

| Field                  | Type         | Description                           |
|------------------------|--------------|---------------------------------------|
| `zabbixtemplate`       | ForeignKey   | Linked Zabbix template                |
| `assigned_object`      | Generic FK   | Device, VM, Site, Tag, etc. (see Assignment Scope) |

Templates can be inherited based on device/site hierarchy.

### `ZabbixTemplateRule`

Regex-driven automatic assignment of a Zabbix template (and optionally a hostgroup and tag) when a Device or VM matches the rule. The pattern is matched against the Platform name only (`re.search`, case-insensitive). Evaluated after direct and inherited `ZabbixTemplateAssignment` rows.

| Field              | Type         | Description |
|--------------------|--------------|-------------|
| `name`             | CharField    | Human-readable name |
| `description`      | CharField    | Optional description |
| `pattern`          | CharField    | Regex matched against Platform name (`re.search`, case-insensitive) |
| `role_pattern`     | CharField    | Optional regex against Device/VM role name; empty = any |
| `require_tags`     | CharField    | Optional comma-separated NetBox tag slugs (all required); empty = any |
| `manufacturer`     | ForeignKey   | Optional `dcim.Manufacturer`; empty = any; `PROTECT` on delete |
| `zabbixtemplate`   | ForeignKey   | Template assigned on match |
| `zabbixhostgroup`  | ForeignKey   | Optional hostgroup assigned on match (`PROTECT`) |
| `zabbixtag`        | ForeignKey   | Optional tag assigned on match (`PROTECT`) |
| `enabled`          | BooleanField | Soft enable/disable |
| `priority`         | IntegerField | Lower = higher priority |

See [Zabbix Template Rules](configuration.md#zabbix-template-rules) for matching behaviour and the hostgroup UI.

### `ZabbixMacro`

Defines a user macro at the Zabbix Server or Zabbix Template level. These macros apply globally to all hosts on the server or to all hosts using the template.

| Field             | Description                                              |
|-------------------|----------------------------------------------------------|
| `macro`           | Macro name, e.g. `{$SNMP_COMMUNITY}`                     |
| `value`           | The macro value                                          |
| `type`            | `Text`, `Secret`, or `Vault secret`                      |
| `description`     | Optional description                                     |
| `assigned_object` | The `ZabbixServer` or `ZabbixTemplate` this belongs to   |

### `ZabbixMacroAssignment`

Assigns a user macro to a specific NetBox object within the inheritance chain (Device, VDC, VM, Site, SiteGroup, Region, Manufacturer, DeviceRole, DeviceType, Platform, Cluster, ClusterType, or Tag).
Macros assigned here override template-level macros of the same name on the resulting Zabbix host.

| Field             | Description                                                                |
|-------------------|----------------------------------------------------------------------------|
| `zabbixmacro`     | The macro definition to assign                                             |
| `value`           | The value for this assignment (may differ from the macro's default value)  |
| `context`         | Optional context suffix, producing e.g. `{$MACRO:context}`                 |
| `is_regex`        | If `True`, the context is treated as a regular expression                  |
| `assigned_object` | The NetBox object this assignment applies to                               |

### `ZabbixHostInterface`

Describes how NetBox IP/DNS maps to Zabbix interfaces.

Includes rich SNMP and TLS configuration fields.

| Field            | Description                                |
|------------------|--------------------------------------------|
| `ip` / `dns`     | IP or DNS to use                           |
| `type`           | Zabbix type (agent, SNMP, IPMI...)         |
| `port`           | Connection port                            |
| `tls_*`          | TLS credentials if applicable              |
| `snmp_*`         | SNMPv3 credentials                         |
| `assigned_object`| Device, VDC, VirtualMachine, ZabbixConfigurationGroup, or Tag |

## Sync & Assignment Models

### `ZabbixServerAssignment`

Links a NetBox object to a Zabbix server/host/proxy.

| Field            | Description                                                       |
|------------------|-------------------------------------------------------------------|
| `zabbixserver`   | Destination server                                                |
| `hostid`         | Zabbix host ID                                                    |
| `zabbixproxy`    | (Optional) specific proxy                                         |
| `assigned_object`| Device, VM, etc.                                                  |
| `sync_enabled`   | Determines if automatic synchronisation from/to Zabbix is enabled |

---

### `ZabbixHostBinding`

Durable mapping from a NetBox Device, VDC or VirtualMachine to a Zabbix `hostid` on a given server. Created and removed by host sync/delete so a host can still be retired after an inherited assignment disappears. There is no operator UI or API.

| Field             | Type         | Description |
|-------------------|--------------|-------------|
| `zabbixserver`    | ForeignKey   | Zabbix server |
| `assigned_object` | Generic FK   | Device, VDC or VirtualMachine |
| `hostid`          | PositiveBigIntegerField | Zabbix host ID |
| `hostname`        | CharField    | Last known hostname (informational) |

---

### `ZabbixHostgroup` / `ZabbixHostgroupAssignment`

Defines host groups and their mapping.

- `ZabbixHostgroup`: static groups defined in Zabbix
- `ZabbixHostgroupAssignment`: assign them to NetBox objects (Jinja `value` or static)

A hostgroup can also be attached by a `ZabbixTemplateRule.zabbixhostgroup` when the rule matches. The hostgroup detail page lists those rules under **Template rules**; the list view shows assignment and rule counts.

#### Nested host groups

Zabbix nesting is a naming convention (`Network/Region/Site`); Zabbix stores no parent relation between groups.

- Creating `A/B/C` never creates `A` or `A/B`. nbxsync therefore creates missing path segments parent-first.
- To rename a group in place, edit the `ZabbixHostgroup` `value` (the Zabbix-facing name). Changing a Jinja template produces a new path; hosts migrate on the next sync and the old path may remain as an empty group.
- Path segments must be non-empty (no leading, trailing or double slashes).

---

### `ZabbixTag` / `ZabbixTagAssignment`

Tags for classification or automation in Zabbix.

---

### `ZabbixHostInventory`

Maps fields to Zabbix's extensive inventory model.

Includes over 70 fields like:

- `hardware`, `vendor`, `asset_tag`
- `site_city`, `site_address_a`
- `os`, `contact`, `poc_*`, etc.

This is populated from NetBox fields or manually if configured.

---

## Proxy & Group Models

### `ZabbixProxy`

Defines a proxy in Zabbix (with advanced TLS and timeout settings).

### `ZabbixProxyGroup`

Groups multiple proxies for failover management.

## Zabbix Maintenance Models

### `ZabbixMaintenance`

Defines a Maintenance object in Zabbix

### `ZabbixMaintenancePeriod`

Linked to a `ZabbixMaintenance`, defines when the maintenance object comes into play

### `ZabbixMaintenanceObjectAssignment`

Defines the assigned objects (Device/Virtual Device Context/VirtualMachine/ZabbixHostgroup) affected by the Zabbix Maintenace

For Zabbix HostGroups, only statically defined objects are supported - as there is no way to resolve any Jinja2-templated hostgroups without the context of the assigned object

### `ZabbixMaintenanceTagAssignment`

Defines the assigned Zabbix Tags affected by the Zabbix Maintenace

For Zabbix Tags, only statically defined objects are supported - as there is no way to resolve any Jinja2-templated value without the context of the assigned object

## Zabbix Configuration Group Models

### `ZabbixConfigurationGroup`

Models a group of configuration settings (such as `ZabbixServer`, `ZabbixHostInterface` et cetera) that are *replicated* to all assigned objects.

Please note that on the `ZabbixHostInterface`, no IP address needs to be entered: upon replicating this to the assigned object, the *primary IP Address* will be used on the `ZabbixHostInterface`

### `ZabbixConfigurationGroupAssignment`

Links a NetBox object to a `ZabbixConfigurationGroup`. Besides Devices, Virtual Device Contexts and VirtualMachines, the group can be assigned on Site, SiteGroup, Region, Manufacturer, Role, DeviceType, Platform, Cluster, ClusterType or Tag so members inherit the group through the inheritance chain. The same object can only be assigned once to the same Configuration Group.

---

## Inheritance Logic

Templates, macros, and hostgroups can be inherited across these chains, by default:

```plaintext
Device / Virtual Device Context
 ├─ Role (and Role parent)
 ├─ DeviceType → Manufacturer
 ├─ Platform → Manufacturer
 ├─ Site → SiteGroup / Region
 └─ NetBox Tags on the object

VirtualMachine
 ├─ Role
 ├─ Platform → Manufacturer
 ├─ Cluster → ClusterType
 ├─ Site / cluster._site → SiteGroup / Region
 └─ NetBox Tags on the object
```

Paths that start with `device` apply to Devices and Virtual Device Contexts. For VirtualMachines they are skipped: since NetBox 4.3, `VirtualMachine.device` points at the hosting device, and walking that path would leak host hardware assignments onto guests.

Tag-targeted assignments are collected from the object's NetBox tags before the `inheritance_chain` paths (first seen wins). See [Inheritance Chain](configuration.md#inheritance-chain).

## Assignment Scope

Not all assignment types can be attached to the same set of NetBox objects.
The table below shows what each model accepts as `assigned_object`.

| Model                                | Can be assigned to |
|--------------------------------------|--------------------|
| `ZabbixMacro`                        | ZabbixServer, ZabbixTemplate |
| `ZabbixServerAssignment`             | Device, VDC, VM, Site, SiteGroup, Region, Manufacturer, DeviceRole, DeviceType, Platform, Cluster, ClusterType, Tag |
| `ZabbixTemplateAssignment`           | Device, VDC, VM, Site, SiteGroup, Region, Manufacturer, DeviceRole, DeviceType, Platform, Cluster, ClusterType, Tag |
| `ZabbixMacroAssignment`              | Device, VDC, VM, Site, SiteGroup, Region, Manufacturer, DeviceRole, DeviceType, Platform, Cluster, ClusterType, Tag |
| `ZabbixTagAssignment`                | Device, VDC, VM, Site, SiteGroup, Region, Manufacturer, DeviceRole, DeviceType, Platform, Cluster, ClusterType, Tag, ZabbixConfigurationGroup |
| `ZabbixHostgroupAssignment`          | Device, VDC, VM, Site, SiteGroup, Region, Manufacturer, DeviceRole, DeviceType, Platform, Cluster, ClusterType, Tag, ZabbixConfigurationGroup |
| `ZabbixHostInterface`                | Device, VDC, VM, ZabbixConfigurationGroup, Tag |
| `ZabbixHostInventory`                | Device, VDC, VM, Site, SiteGroup, Region, Manufacturer, DeviceRole, DeviceType, Platform, Cluster, ClusterType, Tag, ZabbixConfigurationGroup |
| `ZabbixMaintenanceObjectAssignment`  | Device, VDC, VM, ZabbixHostgroup |
| `ZabbixConfigurationGroupAssignment` | Device, VDC, VM, Site, SiteGroup, Region, Manufacturer, DeviceRole, DeviceType, Platform, Cluster, ClusterType, Tag |
