# Dynamic Values

For the `Hostgroup` and `Tag` objects, values can be dynamically assigned using Jinja2 templates. Static values are, of course, also possible.

## Usage

When creating a `Hostgroup` or a `Tag`, you can specify a value, which may be a Jinja2 template. Specifying a template alone does not have any immediate effect; it is the context in which the object is assigned that determines how the Jinja2 template is rendered.

For example, if a Hostgroup is given the value:

```jinja2
{{ object.site.name }}
```

and is applied to a `Device`, it will render as the device's `Site Name`. Here, object refers to the entity to which the assignment is made. This distinction is important: if a `Hostgroup` is assigned to a `DeviceType`, then the `DeviceType` becomes the object—even if the `Hostgroup` is later inherited by a `Device`.

Therefore, using the following template:

```jinja2
{{ object.site.name }}
```

on a `DeviceType` does not make sense, because a `DeviceType` does not have a `Site` attribute.

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
| object      | assigned_object       | Refers to the assigned object; this could be a DeviceType, Device, VirtualMachine, etc.      |
| tag         | zabbixtag.tag         | Contains the Zabbix Tag value that this assignment refers to                                 |
| value       | zabbixtag.value       | The value of the Zabbix Tag (typically the Jinja2 template)                                  |
| name        | zabbixtag.name        | The name of the Zabbix Tag                                                                   |
| description | zabbixtag.description | The description of the Zabbix Tag                                                            |

### Hostgroup

Just like tags, hostgroups are rendered in a context:

| Key         | Value                 | Explanation                                                                                  |
|-------------|-----------------------|----------------------------------------------------------------------------------------------|
| object      | assigned_object       | Refers to the assigned object; this could be a DeviceType, Device, VirtualMachine, etc.      |
| value       | zabbixhostgroup.value | The value of the Zabbix Hostgroup (typically the Jinja2 template)                            |
| name        | zabbixhostgroup.name  | The name of the Zabbix Hostgroup                                                             |
