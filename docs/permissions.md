# Permissions

nbxSync integrates with the [Netbox Permission system](https://netbox.readthedocs.io/en/stable/administration/permissions/).

## Zabbix Hostgroup

**What it is:** Mirrors a Zabbix host group (logical grouping of hosts for permissions, templates, maintenance, etc.).

**How it’s used:** Created locally or discovered from Zabbix, then attached to Devices/VDCs/VMs via **Zabbix Hostgroup Assignment**.

**Typical permissions:**

- _view_ to let operators see the grouping an object will get in Zabbix.
- _add/change/delete_ for engineers curating group structure.

### Permissions

- add_zabbixhostgroup
- change_zabbixhostgroup
- delete_zabbixhostgroup
- view_zabbixhostgroup

## Zabbix Hostgroup Assignment

**What it is:** The through-model that binds a NetBox object (Device/VDC/VM) to one or more Zabbix host groups.

**How it’s used:** Decide host placement in Zabbix UI and ACLs; supports both manual and policy-driven assignments.

**Typical permissions:**

- _view_ for read-only visibility of where things land.
- _add/change/delete_ for engineers orchestrating group membership.

### Permissions

- add_zabbixhostgroupassignment
- change_zabbixhostgroupassignment
- delete_zabbixhostgroupassignment
- view_zabbixhostgroupassignment

## Zabbix Host Interface

**What it is:** The Zabbix Host interface definition for a host.

**How it’s used:** Controls how Zabbix connects (IP vs DNS, port, main/secondary).

**Typical permissions:**

- _view_ for troubleshooting.
- _add/change/delete_ for engineers adjusting connectivity.

### Permissions

- add_zabbixhostinterface
- change_zabbixhostinterface
- delete_zabbixhostinterface
- view_zabbixhostinterface

## Zabbix Host Inventory

**What it is:** Host inventory data synced to Zabbix (e.g., serial, asset tag, location).

**How it’s used:** Populate Zabbix inventory from NetBox attributes; helps search/reporting in Zabbix.

**Typical permissions:**

- _view_ for auditors/operators.
- _add/change/delete_ for those mapping NetBox fields to Zabbix inventory.

### Permissions

- add_zabbixhostinventory
- change_zabbixhostinventory
- delete_zabbixhostinventory
- view_zabbixhostinventory

## Zabbix Macro

**What it is:** A Zabbix user macro definition like `{$ENV}` or `{$SNMP_COMMUNITY}`.

**How it’s used:** Parameterize templates, thresholds, credentials. May be secret.

**Typical permissions:**

- _view_ typically restricted if secrets are present.
- _add/change/delete_ for engineers.

### Permissions

- add_zabbixmacro
- change_zabbixmacro
- delete_zabbixmacro
- view_zabbixmacro

## Zabbix Macro Assignment

**What it is:** Attaches a macro to a specific Device/VDC/VM with precedence over template-level macros.

**How it’s used:** Host-specific overrides—e.g., a unique SNMP community or threshold.

**Typical permissions:**

- _view_ for troubleshooting unexpected values.
- _add/change/delete_ for fine-grained overrides.

### Permissions

- add_zabbixmacroassignment
- change_zabbixmacroassignment
- delete_zabbixmacroassignment
- view_zabbixmacroassignment

## Zabbix Maintenance

**What it is:** A maintenance window definition to suppress alerts or data collection.

**How it’s used:** Schedule planned work to avoid noise and SLA breaches.

**Typical permissions:**

- _view_ for everyone dealing with incidents.
- _add/change/delete_ for engineers

### Permissions

- add_zabbixmaintenance
- change_zabbixmaintenance
- delete_zabbixmaintenance
- view_zabbixmaintenance

## Zabbix Maintenance Object Assignment

**What it is:** Links a maintenance to specific targets (Device/VDC/VM or HostGroup).

**How it’s used:** Choose scope of a maintenance—single device, service group.

**Typical permissions:**

- _view_ to verify coverage.
- _add/change/delete_ for whoever schedules maintenance.

### Permissions

- add_zabbixmaintenanceobjectassignment
- change_zabbixmaintenanceobjectassignment
- delete_zabbixmaintenanceobjectassignment
- view_zabbixmaintenanceobjectassignment

## Zabbix Period (Maintenance Period)

**What it is:** The repeating time blocks that make up a maintenance (e.g., every Sunday 01:00–03:00).

**How it’s used:** Build one-off or recurring maintenance schedules.

**Typical permissions:**

- _view_ to understand timing.
- _add/change/delete_ for engineers.

### Permissions

- add_zabbixmaintenanceperiod
- change_zabbixmaintenanceperiod
- delete_zabbixmaintenanceperiod
- view_zabbixmaintenanceperiod

## Zabbix Maintenance Tag Assignment

**What it is:** A tag selector used to select which items are covered by the maintenace period

**How it’s used:** Dynamic maintenance scoping without enumerating hosts.

**Typical permissions:**

- _view_ for transparency.
- _add/change/delete_ for engineers.

### Permissions

- add_zabbixmaintenancetagassignment
- change_zabbixmaintenancetagassignment
- delete_zabbixmaintenancetagassignment
- view_zabbixmaintenancetagassignment

## Zabbix Proxy

**What it is:** A Zabbix Proxy instance that collects and forwards data for remote segments.

**How it’s used:** Route host checks through a proxy; selected on Zabbix Server Assignments.

**Typical permissions:**

- _view_ for topology visibility.
- _add/change/delete_ for engineers.

### Permissions

- add_zabbixproxy
- change_zabbixproxy
- delete_zabbixproxy
- view_zabbixproxy

## Zabbix Proxy Group

**What it is:** A grouping of proxies for high-level assignments and resilience.

**How it’s used:** Assign hosts or interfaces to a group instead of a single proxy.

**Typical permissions:**

- _view_ for operators.
- _add/change/delete_ for engineers.

### Permissions

- add_zabbixproxygroup
- change_zabbixproxygroup
- delete_zabbixproxygroup
- view_zabbixproxygroup

## Zabbix Server

**What it is:** A connection profile for a Zabbix API endpoint (URL, token, verify SSL certificate).

**How it’s used:** Multi-server/tenant setups; all other Zabbix models point here to know where to sync.

**Typical permissions:**

- _view_ for read-only visibility.
- _add/change/delete_ tightly restricted to platform admins.

### Permissions

- add_zabbixserver
- change_zabbixserver
- delete_zabbixserver
- view_zabbixserver

## Zabbix Server Assignment

**What it is:** Pins a NetBox object (or scope) to a specific Zabbix Server when multiple exist. Allows for assigning multiple servers to a single object

**How it’s used:** Split monitoring across servers; mainly usefull for MSPs

**Typical permissions:**

- _view_ so teams know which server applies.
- _add/change/delete_ for engineers.

### Permissions

- add_zabbixserverassignment
- change_zabbixserverassignment
- delete_zabbixserverassignment
- view_zabbixserverassignment

## Zabbix Tag

**What it is:** A Zabbix host tag (`key`/`value`) used for filtering, correlation, and maintenance targeting.

**How it’s used:** Standardize service/environment metadata (`service=payments`, `env=prod`).

**Typical permissions:**

- _view_ broadly useful.
- _add/change/delete_ for engineers.

### Permissions

- add_zabbixtag
- change_zabbixtag
- delete_zabbixtag
- view_zabbixtag

## Zabbix Tag Assignment

**What it is:** Applies tags to a Device/VDC/VM (or template) so they appear on the Zabbix host/events.

**How it’s used:** Drive alert routing, dashboards, and maintenance selection.

**Typical permissions:**

- _view_ for auditability.
- _add/change/delete_ for service owners.

### Permissions

- add_zabbixtagassignment
- change_zabbixtagassignment
- delete_zabbixtagassignment
- view_zabbixtagassignment

## Zabbix Template

**What it is:** A Zabbix Template reference (collection of items, triggers, discovery, macros).

**How it’s used:** Source of monitoring logic; linked to hosts via **Template Assignment**.

**Typical permissions:**

- _view_ for what a host inherits.
- _add/change/delete_ for engineers.

### Permissions

- add_zabbixtemplate
- change_zabbixtemplate
- delete_zabbixtemplate
- view_zabbixtemplate

## Zabbix Template Assignment

**What it is:** Binds a template to a Device/VDC/VM.

**How it’s used:** Attach monitoring logic to assets; supports layering and overrides.

**Typical permissions:**

- _view_ for visibility.
- _add/change/delete_ for service owners or platform teams.

### Permissions

- add_zabbixtemplateassignment
- change_zabbixtemplateassignment
- delete_zabbixtemplateassignment
- view_zabbixtemplateassignment

## Zabbix Configuration Group

**What it is:** Groups together multiple Zabbix objects which are then replicated to all Assigned Objects

**How it’s used:** Used to 'template' configuration and replicate it to objects linked via **Zabbix Configuration Group Assignments**.

**Typical permissions:**

- _view_ to let operators see the templated configuration
- _add/change/delete_ for engineers curating configuration structure.

### Permissions

- add_zabbixconfigurationgroup
- change_zabbixconfigurationgroup
- delete_zabbixconfigurationgroup
- view_zabbixconfigurationgroup

## Zabbix Configuration Group Assignment

**What it is:** The through-model that binds a NetBox object (Device/VDC/VM) to a single Zabbix Configuration Group

**How it’s used:** Used to assign a single Zabbix Configuration Group to a Device/VDC/VM to replicate the templated configuration

**Typical permissions:**

- _view_ for read-only visibility of where things land.
- _add/change/delete_ for engineers orchestrating group membership.

### Permissions

- add_zabbixconfigurationgroupassignment
- change_zabbixconfigurationgroupassignment
- delete_zabbixconfigurationgroupassignment
- view_zabbixconfigurationgroupassignment
