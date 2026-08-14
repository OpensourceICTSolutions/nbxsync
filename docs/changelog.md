# Changelog

## [Unreleased]
### New features

- Added `exclude_tag` configuration setting to exclude hosts from Zabbix sync entirely via a ZabbixTag assigned to any object in the inheritance chain (`ZabbixTag.tag` name match)
- Added `ZabbixTemplateRule` for regex-based template (and optional hostgroup/tag) assignment by platform name (`re.search`, case-insensitive)
- Template rules support optional conjunctive criteria: `role_pattern`, `require_tags` (NetBox tag slugs) and `manufacturer` (fail-closed when set; `PROTECT` on delete). Optional hostgroup/tag FKs also use `PROTECT`
- Template rules that attach a hostgroup are shown on the Zabbix Hostgroup detail/list views
- Added a REST API endpoint for `ZabbixTemplateRule` (`/api/plugins/nbxsync/zabbixtemplaterule/`)
- Added Site/SiteGroup/Region inheritance paths (appended after role/platform so upgrades do not change Role/Platform precedence); cluster site uses `cluster._site` (available since NetBox 4.2; plugin requires ≥4.2.6)
- Added `ZabbixHostBinding`: a durable record of the Zabbix host owned by each NetBox object, so a host can still be retired after its (inherited) assignment disappears
- Added a background sync job that enumerates Devices/VMs inheriting a Zabbix server assignment, providing zero-touch provisioning for newly created inventory
- Added `allow_inherited_deletion` (default `False`) so inheritance-driven host deletions are reported with their impact before any Zabbix history is discarded
- Added `adopt_existing_hosts` (default `False`) so binding to a pre-existing Zabbix host is an explicit decision instead of a silent takeover. Requires `attach_objtag=True` (identity tags)

### Improvements

- Nested hostgroups: missing path segments (`A/B/C`) are created parent-first in Zabbix so permissions can inherit into subgroups
- Nested hostgroup rename: editing a static group's `ZabbixHostgroup.value` renames the Zabbix group in place via the stored `groupid`
- Configuration Group interfaces are deduplicated by interface identity (type, connect mode, port, DNS, OOB flag), so a second interface of the same Zabbix type is no longer dropped
- A failing host interface no longer hides the failure: per-interface and template-linkage failures are recorded on the assignment and reported as an aggregated job error
- Background host reconciliation collects host primary keys with queryset iterators instead of materialising full Device/VM lists
- Plugin requires NetBox ≥4.2.6 (`PluginConfig.min_version`)
- Inherited sync status on the Zabbix tab uses a neutral indicator (distinct from a direct local assignment)
- Default `backgroundsync.objects.interval` is 360 minutes so a full reconcile is less likely to overlap the next run

### Bug fixes

- Jinja2 tag and hostgroup values are rendered against the Device/VM being synchronised, not against the inheritance source (Role, Platform, Site, …)
- Tag/hostgroup Jinja context exposes `device`, `site`, `tenant`, `role`, `device_type`, and `manufacturer` aliases from the render object (covers #102; aliases follow the host during sync)
- UI previews for hierarchy assignments use a device-shaped view of the target object instead of borrowing a sample descendant device
- UI previews skip Devices/VMs carrying the configured `exclude_tag` when selecting a representative host
- VirtualMachines no longer inherit assignments via `device`-prefixed `inheritance_chain` paths (NetBox ≥4.3 `VirtualMachine.device`). Host manufacturer/role/device-type templates no longer leak onto guest VMs; Virtual Device Contexts still walk those paths
- Deleting a Device/VM in NetBox always retires its Zabbix host (via `ZabbixHostBinding`) even when `sync_enabled` is False on the assignment or server — inventory deletion is intentional retirement, not a background sync

## [1.0.0] - Initial Release

- Loads of features, :)

## [1.0.1] - Major update

### New features

- Zabbix Configuration Groups

### Bug fixes

- API fixes
- Permission fixes
- Database migration fixes for NetBox 4.2.x and lower
- Fixed logic in determining if an host can be synced to Zabbix
- Fixed bug where templates with HTTP agent items required *any* interface, whilst it should be *None*
- Fixed issue where sorting the ZabbixServerAssignmentObjectViewTable on the 'Sync status' column caused an exception
- Fixed issue where sorting on the 'Inherited From' column on the ZabbixInheritedAssignmentTable caused an exception
- Fixed bug where Maintenace windows were to be synced whilst the data wasn't complete

### Breaking changes

None

## [1.0.2] - Major update

### New features

- Implemented logic to use dns_name for the Zabbix Configuration Group assigned Host Interfaces ([#37])
- Implemented the synchronization of the Description field from NetBox to Zabbix ([#36])
- Implemented a checkbox on the Zabbix Host Interface that controls wether the SNMP Community/AuthPass/PrivPass is pushed onto the host (<1.0.2 default behaviour) or not and use the Zabbix inheritance logic  ([#30])
- Implemented new settings to sync the NetBox type and ID to Zabbix as tag: 'attach_objtag' (bool; default True) to enable/disable the tag to be synced; 'objtag_type' to determine the name of the tag that contains the NetBox type and 'objtag_id' to specify the name of the tag that contains the NetBox ID ([#5])

### Bug fixes

- Fixed bug where the 'Zabbix Sync Hosts job' tried to sync ZabbixConfigurationGroups, only to run into an exception ([#38])
- Fixed bug where the object assignment field weren't visible on the Zabbix Macro assignment and Zabbix Host Interface forms, due to translation issues and how this was handled ([#39])
- The lat/long fields on Host Inventory had a strict limit of 16 characters. Whilst correct, this restricted the use of jinja2 syntax. So, this limit has been lifted to 30 characters, which should be sufficient ([#35])
- `api/plugins/nbxsync/zabbixhostinterface/` returned an error when a ZabbixConfigurationGroup has a ZabbixHostInterface assigned; not anymore
- Fixed an issue where only 1 default and 1 non-default Host interface of the same type could be configured (it should be possible to assign multiple non-default interfaces) ([#40])
- Fixed issue where the 'search' API call toward Zabbix was used, whilst 'filter' should be used ([#46])
- Fixed issue where the 'display string' of an object was used, and not the 'name' field. This results in unexpected behaviour when asset tags are configured on devices ([#47])
- Solved issue to ensure the plugin works with NetBox 3.5.0 ([#44])

### Breaking changes

None

## [1.0.3] - Major update

- Updated the documentation

### New features

- Implemented a new API endpoint to trigger the synchronization of a device/vm/vdc to Zabbix
  > Initiating a synchronization is done by POSTing against this endpoint, with the `obj_type` and `obj_id` as data. The `obj_id` is the ID of the `obj_type` that should be synchronized.
  > 
  > For example: `curl -X POST -H "Authorization: Bearer <netbox token>" -H "Content-Type: application/json" -H "Accept: application/json; indent=4" http://<netbox>>/api/plugins/nbxsync/zabbixsync/ --data '{"obj_type": "device", "obj_id": 1}'`
  Possible obj_types: `device`, `virtualmachine`, `virtualdevicecontext`
- Implemented logic to handle the addition of new default Zabbix Host interfaces / changes of Zabbix Host Interfaces ([#57])
- Added support for the 'Max Repetition' field on SNMP Host Interfaces (customer request)
- Implemented the 'sync_enabled' field on Zabbix Server, Zabbix Proxy, Zabbix Proxy Groups and Zabbix Server Assignments control if/what is synchronized to Zabbix ([#66])
- Implemented the 'skip_version_check' field on Zabbix Server to disable checking on supported Zabbix versions ([#74])
- Rewrite the handling of ZabbixConfigurationGroups to work asynchronous and not synchronous; this avoids locking the UI for users when a large number of devices are assigned to a ZabbixConfigurationGroup and a update is applied
- Added links to the Zabbix frontend on the Zabbix Ops view, so operators can easily jump between NetBox and Zabbix for troubleshooting ([#71])

### Bug fixes

- Added the field 'snmpv3_authentication_protocol' to the API for Zabbix Host Interfaces ([#61])
- Updated the field label on Zabbix Proxy Groups (not 'Vendor' but 'Failover delay')
- Fixed logic for Active Zabbix Proxies with a Zabbix Proxy Group set, to include the local_address field ([#59])
- Fixed issue where templates with items of the type 'script' depended on a SNMP Host interface; this is wrong - it should be None. ([#56])
- Fixed issue (again!) where the 'display string' of an object was used, and not the 'name' field. This results in unexpected behaviour when asset tags are configured on devices ([#47] [#63])
- Fixed typo in Netbox permissions ([#62])
- Implemented logic to first synchronize host interfaces based in the usage (default/non default) to avoid errors ([#57])
- Adjusted the 'can_sync' filter so host synchronization only can be triggered if a default host interface exists ([#57])
- Fixed issue where the 'snmp_macro' macro was pushed multiple times when the same HostInterface Type (SNMP) was configured, resulting in errors ([#57])
- Fixed issue that prevented synchronization of hosts to Zabbix when more than one Host Group was assigned in Netbox ([#68])

### Breaking changes

None

## [1.0.4] - Minor update

- Updated the documentation

### New features

- Updated the Zabbix Template Assignment and Zabbix Tag Assignment forms so no duplicate templates/tags can't be assigned ([#78])
- Zabbix Macro's now support Jinja2 templated values ([#83])

### Bug fixes

- Fixed issue with internationalization of field set names on forms ([#39])
- Fixed typo in last_sync_message ([#77])
- Fixed issue with API Schema not being able to generated ([#79])
- Manual device sync fails for templated Zabbix hostgroups when the rendered local hostgroup does not already exist ([#81])
- Ensure that the worker doesn't crash on certain race conditions with regards to the hostinterfacesync job ([#86])
- Fix issue with DeleteHost so it now actually removed the device/object from Zabbix when its deleted from NetBox ([#88])

## [1.0.5] - Minor update

### New features

- Allow configuring a custom hostname and displayname for Zabbix, thanks @bhinz ([#87])
- Implemented 'Trigger dependency sync', thanks to @benjofalanga ([#100])

### Bug fixes

- Fixed issue where syncing to multiple Zabbix Servers failed ([#90])
- Fixed issue where local_address was cleared, even when the proxy is part of a ProxyGroup ([#91])
- Removed duplicate line in ProxySync ([#91])
- Fixed typo (`acept` vs `accept`) in ProxySync ([#91])
- Two bugs in syncmaintenance: missing zabbixserver attribute + invalid "day" parameter for non-MONTHLY timeperiods  ([#107])
- Fixed typo in SyncMaintenceJob
- Fixed issue where only 1 ZabbixServer would be synced
- Fixed the resolution of the pathlabel of a Zabbix Configuration Group
- Fixed issues with HostEvent when multiple ZabbixServers are configured
- Replaced 'gettext' with 'gettext_lazy'

 
### Breaking changes

- Dropped support for NetBox < 4.2.6 in order to support NetBox 4.6.X ([#98])

[#5]: https://github.com/OpensourceICTSolutions/nbxsync/issues/5
[#20]: https://github.com/OpensourceICTSolutions/nbxsync/issues/20
[#35]: https://github.com/OpensourceICTSolutions/nbxsync/issues/35
[#36]: https://github.com/OpensourceICTSolutions/nbxsync/issues/36
[#37]: https://github.com/OpensourceICTSolutions/nbxsync/issues/37
[#38]: https://github.com/OpensourceICTSolutions/nbxsync/issues/38
[#39]: https://github.com/OpensourceICTSolutions/nbxsync/issues/39
[#40]: https://github.com/OpensourceICTSolutions/nbxsync/issues/40
[#44]: https://github.com/OpensourceICTSolutions/nbxsync/issues/44
[#46]: https://github.com/OpensourceICTSolutions/nbxsync/issues/46
[#47]: https://github.com/OpensourceICTSolutions/nbxsync/issues/47
[#56]: https://github.com/OpensourceICTSolutions/nbxsync/issues/56
[#57]: https://github.com/OpensourceICTSolutions/nbxsync/issues/57
[#59]: https://github.com/OpensourceICTSolutions/nbxsync/issues/59
[#61]: https://github.com/OpensourceICTSolutions/nbxsync/issues/61
[#62]: https://github.com/OpensourceICTSolutions/nbxsync/issues/62
[#63]: https://github.com/OpensourceICTSolutions/nbxsync/issues/63
[#66]: https://github.com/OpensourceICTSolutions/nbxsync/issues/66
[#68]: https://github.com/OpensourceICTSolutions/nbxsync/issues/68
[#71]: https://github.com/OpensourceICTSolutions/nbxsync/issues/71
[#74]: https://github.com/OpensourceICTSolutions/nbxsync/issues/74
[#77]: https://github.com/OpensourceICTSolutions/nbxsync/issues/77
[#78]: https://github.com/OpensourceICTSolutions/nbxsync/issues/78
[#79]: https://github.com/OpensourceICTSolutions/nbxsync/issues/79
[#81]: https://github.com/OpensourceICTSolutions/nbxsync/issues/81
[#86]: https://github.com/OpensourceICTSolutions/nbxsync/issues/86
[#87]: https://github.com/OpensourceICTSolutions/nbxsync/issues/87
[#88]: https://github.com/OpensourceICTSolutions/nbxsync/issues/88
[#90]: https://github.com/OpensourceICTSolutions/nbxsync/issues/90
[#91]: https://github.com/OpensourceICTSolutions/nbxsync/issues/91
[#98]: https://github.com/OpensourceICTSolutions/nbxsync/issues/98
[#100]: https://github.com/OpensourceICTSolutions/nbxsync/issues/100
[#107]: https://github.com/OpensourceICTSolutions/nbxsync/issues/107
