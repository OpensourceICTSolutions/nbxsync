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
- Implemented new settings to sync the NetBox type and ID to Zabbix as tag: 'attach_tag' (bool; default True) to enable/disable the tag to be synced; 'objtype_tag' to determine the name of the tag that contains the NetBox type and 'objid_tag' to specify the name of the tag that contains the NetBox ID ([#5])

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

### Links

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