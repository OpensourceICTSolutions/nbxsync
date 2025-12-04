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
- Fixed bug where Maintenance windows were to be synced whilst the data wasn't complete

### Changes
- Increased maximum characters for tls_psk to 1024 (was 255) to support 128 and 256 bit PSKs

### Breaking changes

None
