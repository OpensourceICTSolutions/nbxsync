# Changelog

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