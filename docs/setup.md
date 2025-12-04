# Setup

This plugin requires some setup in Netbox to function correctly.

## Prerequisites

Before you begin, ensure that Netbox can communicate with Zabbix via the [JSON API](https://www.zabbix.com/documentation/current/en/manual/api). Authentication is performed using a `Token`.

Refer to the [Zabbix Documentation](https://www.zabbix.com/documentation/current/en/manual/web_interface/frontend_sections/users/api_tokens) for instructions on generating an API token. Take note of the `Expiration date`. For continuous operation, it is recommended to set no expiration, but for security, you should choose what is most appropriate for your environment.

## Step 1: Set Up Zabbix Server

After generating a token, configure a new Zabbix Server in Netbox. Navigate to `Zabbix` -> `Zabbix Servers` in the left-hand menu and click `Add`.

| Field                      | Value   | Description                                                                              |
|----------------------------|---------|------------------------------------------------------------------------------------------|
| Name                       | String  | The name of the Zabbix Server; used for reference within Netbox.                         |
| URL                        | URI     | The fully qualified URI of the Zabbix frontend, e.g., `http://192.168.2.31/zabbix`       |
| Validate HTTPS Certificate | Boolean | Whether to validate the SSL certificate when using HTTPS.                                |
| Token                      | String  | The authentication token for accessing Zabbix.                                           |

## Step 2: Synchronize Templates

Next, import all templates from Zabbix into Netbox so they can be referenced later. To do this, go to the Zabbix Server you created in Step 1 and click the `Sync Template` button in the upper right corner.

A background job will be scheduled. After a few seconds (if everything works as expected), you should see the templates by navigating to the 'Templates' tab on the Zabbix Server object or by browsing the Zabbix Template objects via the `Zabbix` -> `Zabbix Templates` menu.

## Step 3: Configure a Device / Virtual Machine / Virtual Device Context

Configure your Device, Virtual Device Context (VDC) or Virtual Machine as needed, following the steps below. The main requirements are:

1. The Device, VDC or VM must be associated with a Zabbix Server via a Zabbix Server Assignment.
2. A host interface is required.
3. At least one hostgroup must be assigned.

If these conditions are not met, synchronization will not be possible.

### Step 3a: Assign a Zabbix Server

!!! danger
    A Zabbix Server Assignment is required

First, assign the host to one or more Zabbix Servers. This determines the destination for synchronization. Navigate to the Device, VDC or Virtual Machine, go to the `Zabbix` tab, and look for 'Zabbix Servers' at the top left with a small 'add' button.

When adding an assignment, you can:

- Select the Zabbix Server that should monitor this device.
- Choose the `Zabbix Proxy` or `Zabbix Proxy Group` responsible for monitoring (provided these have already been created in Netbox).

### Step 3b: Configure a Host Interface

!!! danger "Required"
    A Host Interface is required

After assigning a Zabbix Server, specify how the Zabbix Server will monitor the Device, VDC or Virtual Machine via a [Host Interface](https://www.thezabbixbook.com/ch04-zabbix-collecting-data/host-interfaces/).

To configure the Host Interface, navigate to the Device, VDC or Virtual Machine, open the `Zabbix` tab, and find 'Host Interfaces' at the top right with an 'add' button.

When adding a host interface assignment, you must specify:

- The Zabbix Server this Host Interface is synced to
- The Type (Agent, SNMP, JMX, or IPMI)
- Whether to connect via IP address or DNS name
- The port number

At minimum, specify the Type, Port, and either IP Address or DNS name.

### Step 3c: Assign a Hostgroup

!!! danger "Required"
    A Hostgroup assignment is required

!!! note "Hint"
    Hostgroups can be assigned directly to the Device, VDC or VM, or inherited from the DeviceType, Cluster, Manufacturer, Platform, etc. Alternatively, Configuration Groups can be used.

Each host in Zabbix requires at least one Hostgroup. Create a hostgroup using the left-hand menu: `Zabbix` -> `Zabbix Hostgroups` and click `Add`. Ensure the hostgroup is associated with the same Zabbix Server. The value can be static or [dynamically rendered using a Jinja2 template](dynamic_values.md).

Once the Hostgroup is created, create a Hostgroup Assignment on the Device or Virtual Machine.

### Step 3d: Assign a Template

!!! note "Hint"
    Templates can be assigned directly to the Device or VM, or inherited from the DeviceType, Cluster, Manufacturer, Platform, etc. Alternatively, Configuration Groups can be used.


## Debugging

If something does not work as expected, relevant information can usually be found in the Netbox logs or Netbox worker logs. If not, enable Debug mode in Netbox for further troubleshooting.
