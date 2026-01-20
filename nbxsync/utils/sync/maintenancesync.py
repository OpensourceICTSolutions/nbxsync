from datetime import datetime, timedelta

from django.contrib.contenttypes.models import ContentType
from nbxsync.choices import ZabbixMaintenanceTypeChoices, ZabbixTimePeriodTypeChoices
from nbxsync.models import (
    ZabbixHostgroup,
    ZabbixMaintenanceObjectAssignment,
    ZabbixMaintenancePeriod,
    ZabbixMaintenanceTagAssignment,
    ZabbixServerAssignment,
)

from .syncbase import ZabbixSyncBase


class MaintenanceSync(ZabbixSyncBase):
    id_field = 'maintenanceid'
    sot_key = 'maintenance'

    def api_object(self):
        return self.api.maintenance

    def result_key(self):
        return 'maintenanceids'

    def get_create_params(self):
        create_params = {
            'name': self.obj.name,
            'description': self.obj.description,
            'maintenance_type': self.obj.maintenance_type,
            'active_since': int(round(self.obj.active_since.timestamp())),
            'active_till': int(round(self.obj.active_till.timestamp())),
            'timeperiods': self.get_timeperiods(),
            'hosts': self.get_hosts(),
            'groups': self.get_hostgroups(),
        }

        if self.obj.maintenance_type == ZabbixMaintenanceTypeChoices.WITH_COLLECTION:
            create_params['tags_evaltype'] = self.obj.tags_evaltype
            create_params['tags'] = self.get_tags()

        return create_params

    def get_update_params(self, **kwargs):
        params = self.get_create_params()
        params['maintenanceid'] = self.obj.maintenanceid
        return params

    def sync_from_zabbix(self, data):
        try:
            self.obj.save()
            self.obj.update_sync_info(success=True, message='')
        except Exception as _err:
            self.obj.update_sync_info(success=False, message=str(_err))

    def delete(self):
        if not self.obj.maintenanceid:
            try:
                self.obj.update_sync_info(success=False, message='Maintenance already deleted or missing host ID.')
            except Exception as e:
                pass

            return

        try:
            # Delete from Zabbix
            self.api_object().delete([self.obj.maintenanceid])

        except Exception as e:
            # This will update the Zabbix Maintenance object, preventing it from being deleted - just as we'd want (so we can capture the statusmessage)
            self.obj.update_sync_info(success=False, message=f'Failed to delete maintenance: {e}')
            raise RuntimeError(f'Failed to delete maintenace {self.obj.maintenanceid} from Zabbix: {e}')

    def get_timeperiods(self):
        result = []
        for timeperiod in ZabbixMaintenancePeriod.objects.filter(zabbixmaintenance=self.obj):
            timeperiod_result = {
                'period': timeperiod.period,
                'timeperiod_type': timeperiod.timeperiod_type,
            }

            if timeperiod.timeperiod_type == ZabbixTimePeriodTypeChoices.ONE_TIME:
                start_date = datetime.combine(timeperiod.start_date, datetime.min.time()) + timedelta(seconds=timeperiod.start_time)
                timeperiod_result['start_date'] = int(round(start_date.timestamp()))

            if timeperiod.timeperiod_type in [
                ZabbixTimePeriodTypeChoices.DAILY,
                ZabbixTimePeriodTypeChoices.WEEKLY,
                ZabbixTimePeriodTypeChoices.MONTHLY,
            ]:
                timeperiod_result['start_time'] = int(round(timeperiod.start_time))
                timeperiod_result['every'] = int(round(timeperiod.every))

            if timeperiod.timeperiod_type == ZabbixTimePeriodTypeChoices.WEEKLY:
                timeperiod_result['dayofweek'] = 0
                for x in timeperiod.dayofweek:
                    # Bitwise OR, not just sum().
                    timeperiod_result['dayofweek'] |= x

            if timeperiod.timeperiod_type == ZabbixTimePeriodTypeChoices.MONTHLY:
                timeperiod_result['month'] = 0
                for x in timeperiod.month:
                    # Bitwise OR, not just sum().
                    timeperiod_result['month'] |= x

                if len(timeperiod.dayofweek) == 0:
                    timeperiod_result['day'] = timeperiod.day

                if len(timeperiod.dayofweek) > 0:
                    timeperiod_result['dayofweek'] = 0
                    for x in timeperiod.dayofweek:
                        # Bitwise OR, not just sum().
                        timeperiod_result['dayofweek'] |= x

            result.append(timeperiod_result)
        return result

    def get_hosts(self):
        result = []
        zabbixhostgroup_ct = ContentType.objects.get_for_model(ZabbixHostgroup)
        for host in ZabbixMaintenanceObjectAssignment.objects.exclude(assigned_object_type=zabbixhostgroup_ct).filter(zabbixmaintenance=self.obj):
            object_ct = ContentType.objects.get_for_model(host.assigned_object)
            hostid = None
            zabbixserver_assignment = ZabbixServerAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=host.assigned_object_id).first()
            if not zabbixserver_assignment:
                continue

            hostid = zabbixserver_assignment.hostid

            if not hostid:
                continue

            result.append({'hostid': hostid})
        return result

    def get_hostgroups(self):
        result = []
        zabbixhostgroup_ct = ContentType.objects.get_for_model(ZabbixHostgroup)
        for group in ZabbixMaintenanceObjectAssignment.objects.filter(zabbixmaintenance=self.obj, assigned_object_type=zabbixhostgroup_ct):
            zabbixhostgroup = ZabbixHostgroup.objects.get(id=group.assigned_object_id)

            if not zabbixhostgroup.groupid:
                continue

            result.append({'groupid': zabbixhostgroup.groupid})
        return result

    def get_tags(self):
        result = []
        for assigned_tag in ZabbixMaintenanceTagAssignment.objects.filter(zabbixmaintenance=self.obj):
            result.append({'operator': assigned_tag.operator, 'tag': assigned_tag.zabbixtag.tag, 'value': assigned_tag.value})
        return result
