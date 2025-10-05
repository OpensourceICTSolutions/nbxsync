from django.contrib.contenttypes.models import ContentType

from nbxsync.models import ZabbixServerAssignment
from nbxsync.utils.sync import HostSync
from nbxsync.utils.sync.safe_delete import safe_delete

__all__ = ('DeleteHostJob',)


class DeleteHostJob:
    def __init__(self, **kwargs):
        self.instance = kwargs.get('instance')  # This is the Device or VirtualMachine object

    def run(self):
        object_ct = ContentType.objects.get_for_model(self.instance)
        zabbixserver_assignments = ZabbixServerAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=self.instance.pk)

        for assignment in zabbixserver_assignments:
            self.delete_host(assignment)

    def delete_host(self, assignment):
        safe_delete(HostSync, assignment)
