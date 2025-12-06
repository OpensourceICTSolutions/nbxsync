# nbxSync - Netbox ❤️  Zabbix

This plugin integrates [NetBox](https://netbox.dev) with [Zabbix](https://www.zabbix.com/), providing a bridge to synchronize NetBox Devices, Virtual Device Contexts & VMs into Zabbix Hosts and (limited though) vice versa. Through custom models, these Devices, Virtual Device Contexts and VMs can be added to custom hostgroups, macro's can be provisioned with dynamic values (based on jinja2) and templates can be assigned on not only the object itself (so the device/vdc/vm), but can be inherited from Device Types, Manufacturerer, Device Roles and Platform.

In order to ease operational burden, configuration can be grouped together using Configuration Groups. These groups replicate the templated configuration (such as Zabbix Templates, Zabbix Host Interfaces, Hostgroups, et cetera) to the assigned Devices/VDCs/VMs.

## Features

- Sync Devices and VMs as Zabbix hosts (and back)
- Assign and inherit templates
- Manage macros, host groups, and proxy/proxygroups
- Safe deletion and change tracking
- Job-based execution for controlled syncing
- Hostgroup & Tag values based on Jinja2 templates
- Supports Configuration Groups to quickly apply a 'set of configuration items' to Devices, VDCs or VMs

Built to make NetBox the single source of truth while leveraging Zabbix for monitoring.
{: .slogan }

## Screenshots
![Screenshot1](assets/img/screenshot1.png)
![Screenshot2](assets/img/screenshot2.png)
