# Development

We welcome community contributions. However, in order to accept any pull requests, please create an issue first.

When extending or contributing to this plugin:

- Follow the layout: place code in the appropriate directory (`models/`, `forms/`, `filtersets/`, etc.) as described below.
- Define models carefully: prefix new classes with `Zabbix`, add `Assignment` suffix for generic relations, include `sync_info` fields by inheriting `SyncInfoModel`, and create constraints to enforce uniqueness as needed.
- Use the helper functions rather than duplicating logic. For example, call `run_zabbix_operation()` to perform API calls; call `get_assigned_zabbixobjects()` when you need all assignments; `call update_sync_info()` on the model after a sync attempt.
- Adhere to SoT rules: ensure new sync classes define an `id_fiel`, `sot_key` and `api_object()`; inside `get_create_params()` and `get_update_params()`, build the request payload for Zabbix.
- Add inheritance support: if creating new assignment types, decide whether they should be inherited and extend `resolve_inherited_zabbix_assignments()` accordingly.
- Write tests: the repository includes unit tests for models, views, utils and jobs. Any new functionality should be accompanied by tests and follow the branch‑flow described in the docs.
- Update forms/tables/views: whenever you introduce new models or fields, create matching forms (for editing), filtersets (for search), tables (for lists) and views. Use NetBox’s DynamicModelChoiceField for foreign keys and ViewTab to integrate your object into device/VM pages.

## Running Tests

```bash
python3 manage.py test nbxsync
```

## Project Layout

A strict projectlayout is used to ensure code is always found on a logical location

| Folder      | Purpose                                                                                                 |
| ----------- | ------------------------------------------------------------------------------------------------------- |
| `api/`        | DRF serializers & viewsets for plugin models.                                                         |
| `choices/`    | Enumerations for fields, e.g., interface types, TLS methods, SNMP versions.                           |
| `constants/`  | Constant definitions and mappings (e.g., mapping content‑types to form fields).                       |
| `filtersets/` | Django‑filter classes for searchable list views.                                                      |
| `forms/`      | NetBox model forms, bulk‑edit forms and filter forms for each model.                                  |
| `jobs/`       | Job classes that orchestrate synchronisation of hosts, proxies, templates, etc.                       |
| `mixins/`     | Reusable mixins; e.g., ZabbixTabMixin injects a “Zabbix” tab on device/VM pages.                      |
| `models/`     | Django models for servers, proxies, host groups, templates, macros, tags, interfaces and assignments. |
| `migrations/` | Database migrations.                                                                                  |
| `tables/`     | Table classes for list views.                                                                         |
| `templates/`  | HTML templates for UI.                                                                                |
| `static/`     | JavaScript and CSS for custom widgets (e.g., multi‑IP widget).                                        |
| `tests/`      | Unit tests for models, views, utilities and jobs.                                                     |
| `utils/`      | Helper functions, inheritance logic and the synchronisation engine (see below).                       |
| `validators/` | Custom validators (e.g., IP address validator).                                                       |
| `views/`      | CBVs for list/detail views, including bulk‑edit & delete views.                                       |

## Development flow

All development is done in its own branch, named after ```FEATURE/<description>``` or ```BUG/<description>```. Such branch only contains the relevant code: no quick fixes, refactoring or alternations of code that isn't relevant.

Once development is complete, a pull request is created and when approved, this pull request is merged into ```development```. The development serves as staging environment for a new release. Once a new release is created, ```development``` is merged into ```main```. A changelog is created based on the commits. A release is created and tagged with the version number.

Such release is automatically published on PyPi.

## Generic helper functions and synchronisation framework

The plugin provides a number of helper utilities in utils/. New code should reuse these rather than duplicating functionality.

### Attribute resolution

`resolve_attr(obj, "foo.bar")` traverses a dotted attribute path;
`set_nested_attr(obj, "foo.bar", value)` writes to a nested attribute and saves the parent model if necessary.
`resolve_zabbixserver(obj, fallback_path)` tries to determine the ZabbixServer for an object either directly (obj.zabbixserver) or via a fallback path.

### Sync information

All models that are synchronised inherit from SyncInfoModel, which provides `last_sync`, `last_sync_state` and `last_sync_message` fields and an `update_sync_info()` helper. The sync functions update these fields to indicate when an object was last synced and whether it succeeded.

### Connection management

ZabbixConnection is a context manager that logs into a Zabbix API when entering and logs out when exiting. Always use this rather than instantiating zabbix_utils.ZabbixAPI directly.

### Dispatchers

`run_zabbix_operation(sync_class, obj, operation, extra_args)` obtains the target ZabbixServer, establishes a connection and invokes a method (sync, delete, verify_hostinterfaces, etc.) on a sync class.
`safe_sync()` and `safe_delete()` wrap this dispatcher and catch exceptions, returning runtime errors if the operation fails.

### Assignment helpers

`get_assigned_zabbixobjects(instance)` collects all Zabbix assignments for a device/VM (templates, macros, tags, host groups, interfaces, inventory) and merges direct assignments with inherited ones based on the configured inheritance chain.
`get_zabbixassignments_for_request()` wraps this output in table classes for rendering tabs.
`resolve_inherited_zabbix_assignments()` recursively traverses the inheritance chain, gathering assignments from parents and avoiding duplicates.

### Create/update helpers

`create_or_update_zabbixtemplate()` and `create_or_update_zabbixmacro()` are convenience functions that use DRF serializers to create or update ZabbixTemplate and ZabbixMacro records.

### Synchronisation classes

The real synchronisation logic lives under `utils/sync/`. The abstract base class ZabbixSyncBase encapsulates the common pattern of:

- Looking up the object by ID or name in Zabbix; 
- Deciding whether to create or update based on the configured SoT (NetBox or Zabbix);
- Invoking try_create(), sync_to_zabbix(), sync_from_zabbix() and update_in_zabbix() where appropriate. It also resolves the correct ZabbixServer, obtains IDs, and records sync info.

Concrete sync classes: `HostSync`, `HostInterfaceSync`, `HostGroupSync`, `ProxySync`, `ProxyGroupSync` (and others) subclass ZabbixSyncBase. Each implements `api_object()` (returns the appropriate Zabbix API object) and `get_create_params()`/`get_update_params()` to build the payload. For example, HostSync constructs host attributes such as status, proxy settings, macros, host interfaces and inventory based on context; it merges macros defined in NetBox and SNMP macros defined in plugin settings.

### Jobs

The classes under `jobs/` orchestrate sync operations. E.g., `SyncHostJob` obtains all Zabbix assignments for a device/VM, ensures host groups and proxies exist in Zabbix via `safe_sync()`, creates/updates the host with HostSync, synchronises interfaces and then re‑syncs the host. Jobs are triggered via buttons in the UI or the API.

## Naming conventions

The plugin follows predictable naming rules:

`Model names` start with *Zabbix* followed by the *Zabbix entity*. Examples include `ZabbixServer`, `ZabbixProxy`, `ZabbixProxyGroup`, `ZabbixHostgroup`, `ZabbixTemplate`, et cetera. This makes it easy to find the model for a given concept.

`Assignment models` end with *Assignment*. Examples include `ZabbixServerAssignment`, `ZabbixTemplateAssignment`, `ZabbixMacroAssignment`, etc. Each uses a generic foreign key (`assigned_object_type`/`assigned_object_id`) to link a Zabbix object to a NetBox object. The mapping from content type to form field is defined in `ASSIGNMENT_TYPE_TO_FIELD`.

`Zabbix‑side identifiers` in models end in *id*. For example `hostid` is the ID of the host in Zabbix, `groupid` the host‑group ID, `proxyid` the proxy ID, `proxy_groupid` the proxy‑group ID. These fields are nullable because a record may be created locally before it exists in Zabbix.

`Interface types`, `SNMP versions`, `TLS settings` and other enumerations are defined in `choices/` as classes ending in `Choices` and used on models.

Forms, filtersets, tables and views follow the same naming prefix (e.g., ZabbixTemplateForm, ZabbixTemplateFilterForm, ZabbixTemplateTable, ZabbixTemplateListView, ZabbixTemplateEditView, etc.).

Synchronisation classes mirror the Zabbix entity but end in Sync (e.g., HostSync, HostInterfaceSync, ProxySync, ProxyGroupSync, HostGroupSync).
