# Zabbix Maintenance

nbxSync allows you to define Zabbix maintenance windows directly in NetBox and synchronize them to Zabbix. Maintenance windows suppress alerting and, optionally, data collection for a specified set of hosts or host groups during a defined time range.

## Overview

A maintenance window in nbxSync is built from four related objects:
| Object                              | Description                                                                                                                                            |
|-------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| `ZabbixMaintenance`                 | The maintenance window itself: its name, active date range, type, and which Zabbix server it belongs to. This replicates the Zabbix Frontend basically |
| `ZabbixMaintenancePeriod`           | One or more time periods that define *when* within the active range the maintenance is in effect (one-time, daily, weekly, or monthly recurrence)      |
| `ZabbixMaintenanceObjectAssignment` | The hosts or host groups that the maintenance applies to                                                                                               |
| `ZabbixMaintenanceTagAssignment`    | Optional tag-based selectors that further filter which hosts are affected                                                                              |

All four must be configured before a maintenance window can be synchronized to Zabbix.

## `ZabbixMaintenance`

This is the top-level object. Navigate to `Zabbix` → `Zabbix Maintenance` in the left-hand menu and click `Add` to create one.

| Field              | Type       | Description                                                                                       |
|--------------------|------------|---------------------------------------------------------------------------------------------------|
| `name`             | String     | Name of the maintenance window. Must be unique per Zabbix Server                                  |
| `zabbixserver`     | ForeignKey | The Zabbix Server this maintenance window belongs to                                              |
| `active_since`     | DateTime   | The date and time *from* when the maintenance window is active                                    |
| `active_till`      | DateTime   | The date and time *until* when the maintenance window is active                                   |
| `description`      | String     | Optional description                                                                              |
| `maintenance_type` | Choice     | Controls whether data collection continues during maintenance (see below)                         |
| `tags_evaltype`    | Choice     | How tag selectors are combined when `ZabbixMaintenanceTagAssignment` records are used (see below) |

### maintenance_type

| Value                     | Description                                                                            |
|---------------------------|----------------------------------------------------------------------------------------|
| `With data collection`    | Zabbix continues collecting data during the maintenance window. Alerting is suppressed |
| `Without data collection` | Zabbix stops collecting data entirely during the maintenance window                    |

### tags_evaltype

This field controls how multiple `ZabbixMaintenanceTagAssignment` records are evaluated to determine which hosts are in maintenance. It only applies when `maintenance_type` is `With data collection`.

| Value    | Description                                                                                                         |
|----------|---------------------------------------------------------------------------------------------------------------------|
| `And/Or` | A host is in maintenance if it matches all tags with the same tag name, and at least one tag across different names |
| `Or`     | A host is in maintenance if it matches any one of the assigned tags                                                 |

!!! note
    Tag selectors are evaluated by Zabbix, not by NetBox. The `tags_evaltype` value is passed directly to the Zabbix API.

## `ZabbixMaintenancePeriod`

A maintenance window must have at least one period before it can be synchronized. Periods are linked to a `ZabbixMaintenance` and define when within the `active_since`–`active_till` range the maintenance is actually in effect.

Navigate to the `ZabbixMaintenance` object and use the `Add Period` button to create one.

| Field               | Type       | Description                                                                                                                          |
|---------------------|------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `zabbixmaintenance` | ForeignKey | The parent maintenance window                                                                                                        |
| `timeperiod_type`   | Choice     | Recurrence type: one-time, daily, weekly, or monthly                                                                                 |
| `period`            | Integer    | Duration of the maintenance in seconds (between 300 - 86399940)                                                                              |
| `start_date`        | Date       | The calendar date the period starts. Required for **one-time** periods only                                                          |
| `start_time`        | Integer    | Time of day the period starts, expressed as seconds since midnight (0–86400). Required for all types except one-time                 |
| `every`             | Integer    | Recurrence interval (see below)                                                                                                      |
| `dayofweek`         | Array      | Day(s) of the week the period applies. Required for **weekly** periods; optional for **monthly** periods when using day-of-week mode |
| `day`               | Integer    | Day of the month (1–31). Used for **monthly** periods in day-of-month mode                                                           |
| `month`             | Array      | Month(s) the period applies to. Required for **monthly** periods                                                                     |

### timeperiod_type and required fields

The `timeperiod_type` determines which other fields are required and which are ignored. Fields not applicable to the chosen type are not sent to Zabbix.

#### One time only

| Field            | Required                                    |
|------------------|---------------------------------------------|
| `start_date`     | Yes: the calendar date of the maintenance   |
| `start_time`     | Yes: seconds since midnight on `start_date` |
| `period`         | Yes                                         |
| All other fields | Ignored                                     |

#### Daily

| Field            | Required                                                                                          |
|------------------|---------------------------------------------------------------------------------------------------|
| `start_time`     | Yes                                                                                               |
| `every`          | Yes: interval in days (e.g. `1` = every day, `2` = every other day). Defaults to `1` if not set   |
| `period`         | Yes                                                                                                |
| All other fields | Ignored                                                                                           |

#### Weekly

| Field            | Required                                                                                             |
|------------------|------------------------------------------------------------------------------------------------------|
| `start_time`     | Yes                                                                                                  |
| `every`          | Yes: interval in weeks (e.g. `1` = every week, `2` = every other week). Defaults to `1` if not set   |
| `dayofweek`      | Yes: at least one day must be selected                                                               |
| `period`         | Yes                                                                                                  |
| All other fields | Ignored                                                                                              |

#### Monthly

Monthly periods support two modes:
- **day of month** 

*or* 
- **day of week**
 
but **not** both at once.

**Day of month mode** (set `day`, leave `dayofweek` empty):

| Field        | Required                                              |
|--------------|-------------------------------------------------------|
| `start_time` | Yes                                                   |
| `month`      | Yes: one or more months                               |
| `day`        | Yes: day of the month (1–31)                          |
| `every`      | Yes: interval in months. Defaults to `1` if not set.  |
| `period`     | Yes                                                   |

**Day of week mode** (set `dayofweek`, leave `day` empty):

| Field        | Required                                                                                                                                     |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| `start_time` | Yes                                                                                                                                          |
| `month`      | Yes: one or more months                                                                                                                      |
| `dayofweek`  | Yes: one or more days                                                                                                                        |
| `every`      | Yes: which occurrence of the day in the month: `1` = first, `2` = second, `3` = third, `4` = fourth, `5` = last. Defaults to `1` if not set  |
| `period`     | Yes                                                                                                                                          |

!!! warning
    Setting both `day` and `dayofweek` on a monthly period is a validation error. Use one mode or the other.

## `ZabbixMaintenanceObjectAssignment`

Defines which hosts or host groups are included in the maintenance window.A maintenance window must have at least one object assignment **and** at least one `ZabbixMaintenancePeriod` before the Sync button becomes available. Both conditions must be met.

| Field               | Type       | Description                                                                                                                      |
|---------------------|------------|----------------------------------------------------------------------------------------------------------------------------------|
| `zabbixmaintenance` | ForeignKey | The parent maintenance window.                                                                                                   |
| `assigned_object`   | Generic FK | The object to include in the maintenance. Can be a Device, Virtual Device Context, VirtualMachine, or ZabbixHostgroup.           |

Each object can only be assigned once to a given maintenance window.

!!! note
    When assigning a `ZabbixHostgroup`, only hostgroups with **static** values are supported. Hostgroups whose `value` field contains a Jinja2 template cannot be resolved without a device context, so they cannot be used here.

When the maintenance is synced, the assigned Devices, VDCs, and VirtualMachines are resolved to their Zabbix `hostid` values via their `ZabbixServerAssignment`. Objects that have not yet been synchronized to Zabbix (no `hostid`) are silently skipped.

## `ZabbixMaintenanceTagAssignment`

Optionally, a maintenance window can use tag selectors to dynamically determine which hosts are in maintenance, in addition to or instead of explicit object assignments. This is evaluated by Zabbix.

| Field               | Type       | Description                                          |
|---------------------|------------|------------------------------------------------------|
| `zabbixmaintenance` | ForeignKey | The parent maintenance window                        |
| `zabbixtag`         | ForeignKey | The `ZabbixTag` to match against                     |
| `operator`          | Choice     | How the tag value is matched: `Equals` or `Contains` |
| `value`             | String     | The tag value to match                               |

Each tag can only be assigned once per maintenance window.

!!! note
    Only `ZabbixTag` objects with **static** values are supported here. Tags whose `value` field contains a Jinja2 template cannot be used as maintenance tag selectors.

!!! note
    Tag selectors only apply when `maintenance_type` is `With data collection`. The `tags_evaltype` field on the parent `ZabbixMaintenance` controls how multiple tag selectors are combined.

## When can a maintenance window be synced?

The Sync button appears on a `ZabbixMaintenance` object only when all of the following are true:

- At least one `ZabbixMaintenancePeriod` exists.
- At least one `ZabbixMaintenanceObjectAssignment` exists (pointing to a host, VDC, VM, or host group).

If either condition is not met, the Sync button is hidden.

Additionally, if `sync_enabled` is set to `False` on the associated `ZabbixServer`, the sync job exits immediately without making any API calls.

## Synchronization

Syncing a maintenance window is triggered in two ways:

- **Manually** via the Sync button on the `ZabbixMaintenance` detail page.
- **Automatically** via the `Zabbix Sync Maintenance job` background system job, which runs at the interval configured by `backgroundsync.maintenance.interval` (default: every 15 minutes). Only maintenance windows that pass the `can_sync` check are included in the automatic run.

Both paths enqueue a `syncmaintenance` background job on the RQ `low` queue, which is then picked up by a worker.

When a `ZabbixMaintenance` object is **deleted** from NetBox, a `deletemaintenance` background job is automatically enqueued via a `pre_delete` signal. This job deletes the corresponding maintenance window from Zabbix before the NetBox record is removed.

## Automatic maintenance windows

nbxSync can create maintenance windows automatically when a device or VM's NetBox status maps to the `enabled_in_maintenance` action in `statusmapping`. This happens during a host sync, not as a separate operation.

When a host sync runs and the status mapping resolves to `enabled_in_maintenance`, the sync engine checks whether an automatically created maintenance window already exists for that host. If not, it creates one:

- The maintenance window is named `[AUTOMATIC] <device name>`.
- `active_since` is set to the current time.
- `active_till` is set to `active_since` plus `maintenance_window_duration` seconds (default: 3600).
- A single one-time `ZabbixMaintenancePeriod` is created for the same duration, starting at the current time.
- The host is added as a `ZabbixMaintenanceObjectAssignment`.
- The maintenance window is immediately synced to Zabbix.

When the host's status changes away from `enabled_in_maintenance` on the next sync, the automatically created maintenance window is deleted from both NetBox and Zabbix.

Automatically created maintenance windows have `automatic = True` and cannot be manually edited in a way that would prevent this cleanup logic from working. Manual maintenance windows (`automatic = False`) are never touched by this mechanism.

See [`maintenance_window_duration`](configuration.md) for the configuration option that controls the duration.