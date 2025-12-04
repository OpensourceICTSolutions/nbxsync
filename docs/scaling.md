# Scaling

This plugin uses the [NetBox Scheduled Job feature](https://netboxlabs.com/docs/netbox/features/background-jobs/) to schedule background jobs. These tasks are then processed by one or more workers. By default, NetBox starts only a single worker.

Each worker can run only one job at a time, meaning tasks are processed serially. If you need to synchronize a large number of objects between NetBox and Zabbix, a single worker may take a long time to work through the backlog.

To improve throughput, you can increase the number of workers so tasks run in parallel. However, be aware that this will also increase the number of API calls to your Zabbix instance, potentially overloading it, so scale carefully.

## Examples

The examples below are provided for reference only. There’s no guarantee they will work exactly as shown in your environment or continue working across NetBox upgrades. Always verify before applying changes.

### Native installations

The `{1..5}` portion defines how many workers will be spawned.

```bash
# Copy the netbox-rq.service file; the @ indicates this is a template
cp /etc/systemd/system/netbox-rq.service /etc/systemd/system/netbox-rq@.service

# Reload systemd to pick up the templated service
systemctl daemon-reload

# Stop and disable the original single worker
systemctl stop netbox-rq
systemctl disable netbox-rq

# Start 5 new workers
systemctl enable --now netbox-rq@{1..5}.service
```

To restart the workers after an upgrade:

```bash
systemctl restart netbox-rq@{1..5}.service
```

### Dockerized setup

Update your Docker Compose file and add the `deploy` -> `replicas` value. The number of replicas determines how many workers will run.

```python title="docker-compose.yml"
  netbox-worker:
    <<: *netbox
    depends_on:
      netbox:
        condition: service_healthy
    command:
      - /opt/netbox/venv/bin/python
      - /opt/netbox/netbox/manage.py
      - rqworker
    healthcheck:
      test: ps -aux | grep -v grep | grep -q rqworker || exit 1
      start_period: 20s
      timeout: 3s
      interval: 15s
    deploy:
      mode: replicated
      replicas: 2
```
