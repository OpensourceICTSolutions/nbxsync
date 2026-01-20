# nbxSync – NetBox ⇄ Zabbix Integration

**Integrate Netbox as Source of Truth with Zabbix as Monitoring Solution**

![CI](https://github.com/OpensourceICTSolutions/nbxsync/actions/workflows/ci.yml/badge.svg)
![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/bvbaekel/1a1cf04e63a52d5497edd6e0a564ec2b/raw/4a293f964b246091d1fd943629408dbb7d9f597f/cov.json)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![NetBox](https://img.shields.io/badge/NetBox-4.2|4.3|4.4|4.5-blue.svg)

---

## Description

nbxSync seamlessly integrates Netbox with Zabbix.

With nbxSync you can:
✅ Create and manage all your devices in NetBox (your single source of truth)
✅ Automatically sync devices to Zabbix for monitoring
✅ Save time, reduce errors, and ensure consistent, up-to-date monitoring data

This plugin bridges the gap between network/source-of-truth documentation and infrastructure monitoring – something many teams have been asking for.

💡 If you’re running both NetBox and Zabbix, this is the missing link you’ve been waiting for.

## Compatibility

| Release | Minimum NetBox Version | Maximum NetBox Version |
| ------- | ---------------------- | ---------------------- |
| 1.0.2   | 4.2.0                  | 4.5.x                  |
| 1.0.1   | 4.2.0                  | 4.4.x                  |
| 1.0.0   | 4.3.0                  | 4.4.x                  |

---

## 📦 Installation

### 1. Install the plugin

> [!IMPORTANT]
> The steps below are for a non-dockerized setup. If you run Netbox in Docker containers, please see [their installation instructions](https://netboxlabs.com/docs/netbox/installation/)

Install using pip

```bash
pip install nbxsync
```

### 2. Enable the plugin in `configuration.py`

Add to your `PLUGINS` list:

```python
PLUGINS = [
    'nbxsync',
    # ... other plugins ...
]
```

### 3. Apply migrations and collect static files

```bash
python3 manage.py migrate
python3 manage.py collectstatic
```

### 4. Restart NetBox

```bash
sudo systemctl restart netbox netbox-rq
```

---

## Screenshots

![Screenshot 1](docs/assets/img/screenshot1.png "Device Zabbix overview")
---

![Screenshot 2](docs/assets/img/screenshot2.png "Device Zabbix Ops overview")
---
