# Models & Objects

This plugin defines a set of Django models to represent and synchronize NetBox objects with their counterparts in Zabbix.

---

## Core Models

### `ZabbixServer`

This model represents the Zabbix Server where objects are synced from / to.

| Field            | Type         | Description                         |
|------------------|--------------|-------------------------------------|
| `name`           | CharField    | Friendly name of the server         |
| `description`    | CharField    | Optional description                |
| `url`            | URLField     | Full API endpoint URL               |
| `token`          | CharField    | API token for authentication        |
| `validate_certs` | BooleanField | Toggle SSL cert validation          |

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
| `assigned_object`      | Generic FK   | Device, VM, Interface, etc.           |

Templates can be inherited based on device/site hierarchy.

---

### `ZabbixMacro` / `ZabbixMacroAssignment`

Used to assign custom macros to hosts/templates.

- `ZabbixMacro` defines a macro.
- `ZabbixMacroAssignment` links it to a NetBox object with value and context.

| Field             | Description                             |
|-------------------|-----------------------------------------|
| `macro`           | Macro name (e.g. `{HOST.NAME}`)         |
| `value`           | Static or regex-based value             |
| `assigned_object` | Target device/interface/etc.            |

---

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
| `assigned_object`| Mapped to NetBox interface or device       |

---

## Sync & Assignment Models

### `ZabbixServerAssignment`

Links a NetBox object to a Zabbix server/host/proxy.

| Field            | Description                      |
|------------------|----------------------------------|
| `zabbixserver`   | Destination server               |
| `hostid`         | Zabbix host ID                   |
| `zabbixproxy`    | (Optional) specific proxy        |
| `assigned_object`| Device, VM, etc.                 |

---

### `ZabbixHostgroup` / `ZabbixHostgroupAssignment`

Defines host groups and their mapping.

- `ZabbixHostgroup`: static groups defined in Zabbix
- `ZabbixHostgroupAssignment`: assign them to NetBox objects

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

Models a group of configuration settings (such as `ZabbixServer`, `ZabbixHostInterface` et cetera) that are *replicated* to all assigned Devices, Virtual Device Contexts or VirtualMachines.

Please note that on the `ZabbixHostInterface`, no IP address needs to be entered: upon replicating this to the assigned object, the *primary IP Address* will be used on the `ZabbixHostInterface`

### `ZabbixConfigurationGroupAssignment`

Links a Device/Virtual Device Context/VirtualMachine to a `ZabbixConfigurationGroup` and as such determines the applied configuration on the linked object. Device/Virtual Device Context/VirtualMachines can only be assigned to a single `ZabbixConfigurationGroup`


---

## 🧬 Inheritance Logic

Templates, macros, and hostgroups can be inherited across these chains, by default:

```plaintext
Manufacturer → Device Type      → Platform     → Role       → Device
Cluster      → VirtualMachine
```

However, this is [configurable](configuration.md).
