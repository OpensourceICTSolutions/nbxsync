# Zabbix Configuration Groups — How They Work

## Overview

A `ZabbixConfigurationGroup` is a **reusable configuration template** that lets you define a set of Zabbix assignments **once** and have them automatically propagated to many NetBox objects (Devices, Virtual Machines, VirtualDeviceContexts).

Think of it as a "profile": you attach Zabbix servers, templates, tags, host groups, macros and host interfaces to the group itself, then assign that group to individual devices/VMs. Whenever a device is added to the group, it immediately inherits all of those Zabbix configurations automatically.

---

## Data Model

### `ZabbixConfigurationGroup`

```python
class ZabbixConfigurationGroup(NetBoxModel):
    name        = CharField(max_length=512)
    description = CharField(max_length=1024, blank=True)
```

A minimal model, just a name and a description. All the complexity lives in assignments and signals around it. It inherits `NetBoxModel`, giving it standard NetBox features: changelog, tags, custom fields, creation/update timestamps, etc.



### `ZabbixConfigurationGroupAssignment`

```python
class ZabbixConfigurationGroupAssignment(NetBoxModel):
    zabbixconfigurationgroup = ForeignKey('nbxsync.ZabbixConfigurationGroup', ...)
    assigned_object_type     = ForeignKey(ContentType, limit_choices_to=DEVICE_OR_VM_ASSIGNMENT_MODELS, ...)
    assigned_object_id       = PositiveBigIntegerField(...)
    assigned_object          = GenericForeignKey(...)
```

This is the **membership record**: it links a group to a specific Device, VirtualMachine or VirtualDeviceContext (enforced by `DEVICE_OR_VM_ASSIGNMENT_MODELS`). A unique constraint prevents the same object from being added to the same group twice.

The important distinction: this is **not** about Zabbix config per se — it is purely about group membership. The actual Zabbix config is stored on the group itself via the normal assignment models (see below).

---

## The Dual Role of Existing Assignment Models

The existing nbxsync assignment models (`ZabbixServerAssignment`, `ZabbixTemplateAssignment`, `ZabbixTagAssignment`, `ZabbixHostgroupAssignment`, `ZabbixMacroAssignment`, `ZabbixHostInterface`) all have two distinct modes of operation:

| Mode | `assigned_object` points to | `zabbixconfigurationgroup` field |
|---|---|---|
| **Direct assignment** | A Device / VM / VDC | `NULL` |
| **Group-level definition** | A `ZabbixConfigurationGroup` | `NULL` |
| **Group-cloned copy** | A Device / VM / VDC | FK to the originating group |

The `zabbixconfigurationgroup` FK on each assignment model is the "provenance" marker: a non-null value means this record was **created by the group propagation system**, not by a human directly. This matters for the "don't overwrite manual assignments" logic (described below).

The `ASSIGNMENT_MODELS` constant is intentionally broader than `DEVICE_OR_VM_ASSIGNMENT_MODELS` — it includes manufacturer, device role, device type, cluster, etc. — so group-level definitions (`assigned_object = ZabbixConfigurationGroup`) are technically stored using the same generic FK pattern used for all direct assignments.

---

## How Propagation Works — Step by Step

When a device or VM is added to a group, the system propagates every piece of Zabbix config from the group to that device. This flow is driven by **Django signals** that dispatch **RQ background jobs**, which in turn execute the actual database mutations safely after the transaction commits.

### Step 1 — Membership is saved

A `ZabbixConfigurationGroupAssignment` is created or updated (device → group link).

### Step 2 — `post_save` signal fires and enqueues an RQ job

```python filename="test"
@receiver(post_save, sender=ZabbixConfigurationGroupAssignment)
def handle_postsave_zabbixconfigurationgroupassignment(sender, instance, created, **kwargs):
    if instance.zabbixconfigurationgroup is None:
        return

    propagate_configgroup_assignment.delay(instance.pk)
```

The signal does not run propagation inline. It enqueues a `propagate_configgroup_assignment` background job on the RQ `low` queue and returns immediately, so the HTTP request that triggered the save is not blocked.


### Step 3 — The job runs `resync_zabbixconfigurationgroupassignment`

A worker picks up the job and calls `PropagateConfigGroupAssignmentJob.run()`, which calls `resync_zabbixconfigurationgroupassignment(instance)` — the main propagation engine in `utils/cfggroup/resync_zabbixconfiggroupassignment.py`.

For each assignment type it:

1. Looks up all group-level definitions for this config group (e.g. all `ZabbixServerAssignment` records where `assigned_object = this_configgroup`).
2. For each one, calls `propagate_group_assignment()`.

### Step 4 — `propagate_group_assignment` iterates members

```python
def propagate_group_assignment(*, instance, model, lookup_factory, ...):
    def _do():
        for assigned in iter_configgroup_members(instance):
            lookup = lookup_factory(instance, assigned)

            # Don't overwrite manual (non-group-sourced) assignments
            existing = model.objects.filter(**lookup).first()
            if existing is not None and getattr(existing, respect_existing_null_group_field) is None:
                continue

            defaults = build_defaults_from_instance(instance, exclude=..., extra={'zabbixconfigurationgroup': ...})

            try:
                model.objects.update_or_create(**lookup, defaults=defaults)
            except IntegrityError:
                model.objects.filter(**lookup).update(**defaults)

    transaction.on_commit(_do)
```

`iter_configgroup_members()` queries all `ZabbixConfigurationGroupAssignment` records for the group, giving us every device/VM that belongs to the group.

For each member, it upserts the assignment record on that device, copying all non-excluded fields from the group-level definition and stamping `zabbixconfigurationgroup` with the group FK.

The actual mutations are wrapped in `transaction.on_commit(_do)`, so they only execute after the job's own database transaction commits. This prevents partial state from ever being visible.

### Step 5 — Special handling for HostInterfaces

Host interfaces get separate treatment because they require an IP address. After all other assignment types are processed, a `transaction.on_commit` callback runs the interface propagation:

```python
for parent in hostinterface_parents:
    for assigned in iter_configgroup_members(parent):
        primary_ip = getattr(assigned.assigned_object, 'primary_ip', None)
        if not primary_ip:
            continue  # skip devices with no primary IP

        ZabbixHostInterface.objects.update_or_create(
            **lookup,
            defaults={..., 'ip': primary_ip, 'dns': primary_ip.dns_name, ...}
        )
```

Because the group-level `ZabbixHostInterface` has no IP (it can't — it's on the group, not a device), the IP is pulled from the device's `primary_ip` at propagation time. The group-level record stores the interface type, port, SNMP config etc., and the IP is injected per-device.

---

## The Reverse: Cleanup on Removal

When a `ZabbixConfigurationGroupAssignment` is deleted (device leaves the group), the `post_delete` signal enqueues a cleanup job:

```python
@receiver(post_delete, sender=ZabbixConfigurationGroupAssignment)
def handle_postdelete_zabbixconfigurationgroupassignment(sender, instance, **kwargs):
    if instance.zabbixconfigurationgroup is None:
        return

    delete_configgroup_assignment_children.delay(
        configgroup_pk=instance.zabbixconfigurationgroup.pk,
        assigned_object_type_pk=instance.assigned_object_type_id,
        assigned_object_id=instance.assigned_object_id,
    )
```

The `DeleteConfigGroupAssignmentChildrenJob` that runs in the worker removes all group-cloned assignments from the departing device across every assignment type:

```python
ZabbixServerAssignment.objects.filter(**filter_kwargs).delete()
ZabbixTemplateAssignment.objects.filter(**filter_kwargs).delete()
ZabbixTagAssignment.objects.filter(**filter_kwargs).delete()
ZabbixHostgroupAssignment.objects.filter(**filter_kwargs).delete()
ZabbixMacroAssignment.objects.filter(**filter_kwargs).delete()
ZabbixHostInterface.objects.filter(**filter_kwargs).delete()
```

Only records stamped with this group's FK are deleted. Manually created assignments (where `zabbixconfigurationgroup=NULL`) are untouched.

---

## Bidirectional Sync: Group Config Changes Propagate Too

When a group-level assignment is **created or updated** (e.g. you add a new Zabbix template to the group), the assignment model's own `post_save` signal enqueues a targeted propagation job:

```python
@receiver(post_save, sender=ZabbixServerAssignment)
def handle_sync_zabbixserverassignment(sender, instance, **kwargs):
    if not is_configgroup_assignment(instance):
        return  # Only act on group-level definitions

    propagate_server_assignment.delay(instance.pk)
```

`is_configgroup_assignment()` checks whether `assigned_object_type` points to `ZabbixConfigurationGroup`. If it does, the corresponding propagation job is enqueued. If it's a direct device/VM assignment, nothing happens.

Each assignment type has its own pair of propagation and cleanup jobs (`propagate_server_assignment` / `delete_server_assignment_clones`, `propagate_template_assignment` / `delete_template_assignment_clones`, and so on). When a group-level assignment is **deleted** (e.g. a template is removed from the group), the matching delete job removes the cloned assignments from all current group members.

---

## The "Don't Overwrite Manual Assignments" Guard

A subtle but important safety mechanism: if a device already has a direct (non-group) assignment for the same Zabbix server/template/etc., the propagation system **skips it**:

```python
existing = model.objects.filter(**lookup).first()
if existing is not None and getattr(existing, 'zabbixconfigurationgroup') is None:
    continue
```

If `zabbixconfigurationgroup` is `None` on the existing record, it means a human put it there manually. The propagation leaves it alone and does not overwrite it with the group-sourced version.

---

## `resync_all_assignments` — Manual Re-trigger

The `ZabbixConfigurationGroup` model exposes a `resync_all_assignments()` method:

```python
def resync_all_assignments(self):
    for assignment in self.zabbixconfigurationgroupassignment.all():
        resync_zabbixconfigurationgroupassignment(assignment)
```

This iterates all current members of the group and re-runs the full propagation for each. Useful when you want to force a full resync — e.g. after bulk-importing group members, or after fixing a bug.

---

## Summary Diagram

```
ZabbixConfigurationGroup  (e.g. "Router Profile")
│
├── ZabbixServerAssignment (assigned_object → ZabbixConfigurationGroup)
│     └── defines: which Zabbix server, proxy, sync settings
│
├── ZabbixTemplateAssignment (assigned_object → ZabbixConfigurationGroup)
│     └── defines: which templates to apply
│
├── ZabbixTagAssignment / ZabbixHostgroupAssignment / ZabbixMacroAssignment
│
├── ZabbixHostInterface (assigned_object → ZabbixConfigurationGroup)
│     └── defines: interface type, port, SNMP/TLS config (NO IP — injected per device)
│
└── ZabbixConfigurationGroupAssignment  ←── membership records
      ├── → Device: router-01
      ├── → Device: router-02
      └── → VirtualMachine: vm-03

On membership save/delete:
  Signal → enqueues RQ job (low queue)
         → job calls resync_zabbixconfigurationgroupassignment()
         → propagate_group_assignment() for each assignment type
         → upsert/delete cloned records on each member device/VM
         → DB mutations deferred via transaction.on_commit()
```

---

## Key Design Properties

| Property                 | Detail                                                                                                                                              |
|--------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| **Generic FK pattern**   | Groups are assigned to devices the same way any other NetBox object is, using `ContentType` + `object_id`                                           |
| **Provenance tracking**  | Cloned records carry a `zabbixconfigurationgroup` FK so they can be distinguished from manual assignments and cleaned up correctly                  |
| **Non-destructive**      | Manual (non-group) assignments on a device are never overwritten by propagation                                                                     |
| **Asynchronous**         | All propagation runs in RQ background jobs on the `low` queue, so the request that triggered the change returns immediately without blocking the UI |
| **Transactionally safe** | Within each job, DB mutations run inside `transaction.on_commit()` callbacks, so partial state is never exposed                                     |
| **Bidirectional**        | Changes to group membership AND changes to group-level config both trigger propagation                                                              |
| **IP injection**         | Host interfaces are a special case: the IP is pulled from the device's `primary_ip` at propagation time, not stored on the group                    |
