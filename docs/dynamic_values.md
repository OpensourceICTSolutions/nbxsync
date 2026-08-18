# Dynamic Values

For the `Hostgroup`, `Tag` and `ZabbixHostInventory` objects, values can be dynamically assigned using Jinja2 templates. Static values are, of course, also possible.

## Usage

When creating a `Hostgroup`, `Tag`, or a `ZabbixHostInventory`, you can specify a value, which may be a Jinja2 template. Specifying a template alone does not have any immediate effect; it is the context in which the object is assigned that determines how the Jinja2 template is rendered.

For example, if a Hostgroup is given the value:

```jinja2
{{ object.site.name }}
```

and is applied to a `Device`, it will render as the device's Site name.

During host synchronisation, tag, macro and host-inventory templates are rendered against the Device, VDC or VirtualMachine being synced — even when the assignment is inherited. Hostgroup templates still render with `object` as the assignment target, so hostgroup Jinja that needs host fields should be assigned where those fields exist.

## Context

Rendering a value is always performed within a context, which provides access to various values. While the object reference has already been explained, there are additional context variables available. These values can be used in the Jinja2 template, by referring to it.

```jinja2
{{ object.site.name }} (via {{ tag }})
```

would be perfectly valid.

### Tag

Tags are rendered within a context that includes the following information:

| Key         | Value                 | Explanation                                                                                  |
|-------------|-----------------------|----------------------------------------------------------------------------------------------|
| object      | assigned_object       | The assignment target. During host sync this is the Device/VM/VDC being synced |
| tag         | zabbixtag.tag         | Contains the Zabbix Tag value that this assignment refers to |
| value       | zabbixtag.value       | The value of the Zabbix Tag (typically the Jinja2 template) |
| name        | zabbixtag.name        | The name of the Zabbix Tag |
| description | zabbixtag.description | The description of the Zabbix Tag |

### Hostgroup

Just like tags, hostgroups are rendered in a context:

| Key         | Value                 | Explanation |
|-------------|-----------------------|-------------|
| object      | assigned_object       | The assignment target (not overridden to the synced host during host sync) |
| value       | zabbixhostgroup.value | The value of the Zabbix Hostgroup (typically the Jinja2 template) |
| name        | zabbixhostgroup.name  | The name of the Zabbix Hostgroup |

### Host Inventory

Each field on a `ZabbixHostInventory` record is rendered individually. The context is simpler than for tags and hostgroups:

| Key      | Value            | Explanation |
|----------|------------------|-------------|
| `object` | assigned_object  | The assignment target. During host sync this is the Device/VM/VDC being synced |

Inventory can be assigned on hierarchy objects and inherited; during host sync `object` is the host, so fields such as `object.site.name` or `object.primary_ip` resolve correctly.

Note that each field has a maximum character length enforced at render time, values that exceed the limit are silently truncated. The `inventory_mode` field controls how Zabbix treats the inventory:
- `Manual` (the default) means Zabbix only updates inventory via the API, which is how nbxSync writes it. 
- `Automatic` would cause Zabbix to overwrite inventory fields from item values, which conflicts with nbxSync's writes and should generally be avoided.

!!! note
    The `inventory_mode` field determines how Zabbix handles the inventory data.
    - Manual (default) means only nbxSync writes to inventory.
    - Automatic causes Zabbix to overwrite inventory from item values (this conflicts with nbxSync's writes and is not recommended).
    - Disabled turns off inventory entirely for the host.