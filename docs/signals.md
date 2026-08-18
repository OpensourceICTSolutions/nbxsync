# Signals & Background Jobs

nbxSync uses Django signals to detect changes in NetBox and automatically dispatch background jobs via RQ (Redis Queue). No synchronization happens synchronously during a request — all Zabbix API calls run in a worker process.

## Device / VM deletion

When a Device or VirtualMachine is deleted in NetBox, a `pre_delete` signal fires synchronously and immediately removes all associated nbxSync records from the NetBox database:

- `ZabbixHostInventory`
- `ZabbixHostInterface`
- `ZabbixTemplateAssignment`
- `ZabbixHostgroupAssignment`
- `ZabbixTagAssignment`
- `ZabbixMacroAssignment`

If **NetBox is the Source of Truth** for hosts (`sot.host = 'netbox'`), a `deletehost` background job is also enqueued on the RQ `low` queue, which deletes the corresponding Zabbix host via `ZabbixHostBinding`. This retirement runs even when `sync_enabled` is False on the assignment or server: deleting the NetBox object is an intentional decommission, not a background sync.

If **Zabbix is the Source of Truth** for hosts, the `ZabbixServerAssignment` is deleted from NetBox instead, and no deletion is sent to Zabbix.

## Configuration Group changes

When a `ZabbixConfigurationGroupAssignment` is saved or deleted (i.e. a device/VM is added to or removed from a Configuration Group), a background job is dispatched via RQ to propagate the change:

- **On save**: a `propagate_configgroup_assignment` job is enqueued, which  copies all group-level configuration to the newly assigned object.
- **On delete**: a `delete_configgroup_assignment_children` job is enqueued, which removes all group-sourced assignments from the departing object.

Similarly, when a group-level assignment is itself created, updated, or deleted (e.g. a new template is added to a Configuration Group), the matching propagation job runs for all current members of the group.

All of these jobs run on the RQ `low` queue and require a running worker.