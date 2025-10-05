# Traffic flows

NetBox is composed of several components, most importantly the Django application (the frontend) and one or more workers.

- Job handling: nbxSync dispatches jobs into a queue. These jobs are then picked up and executed by a worker. This is native Netbox functionality. 
- Zabbix communication: When a job is executed, the worker communicates with the Zabbix API. Depending on the configuration, this communication happens over port 80 (HTTP, unencrypted) or port 443 (HTTPS, encrypted).
- Operational View: If the Zabbix Operational View feature is enabled, the NetBox frontend also communicates directly with the Zabbix API to retrieve problems and events for a given host.

## Traffic Matrix

The following table summarizes the traffic flows and the firewall rules that must be in place for proper operation:

| Source          | Destination     | Protocol / Port  | Description                                        |
| --------------- | --------------- | ---------------- | -------------------------------------------------- |
| Clients         | NetBox frontend | TCP 80 / TCP 443 | Standard access to the NetBox web interface        |
| NetBox frontend | Zabbix frontend | TCP 80 / TCP 443 | Used for Zabbix Operational View (problems/events) |
| NetBox worker   | Zabbix frontend | TCP 80 / TCP 443 | Used for object synchronization and related tasks  |
