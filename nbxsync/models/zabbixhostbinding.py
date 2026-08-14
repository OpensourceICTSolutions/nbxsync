from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from netbox.models import NetBoxModel

__all__ = ('ZabbixHostBinding',)


def _limit_assigned_objects():
    """Lazy import for ``limit_choices_to`` to avoid model/constants cycles."""
    from nbxsync.constants import DEVICE_OR_VM_ASSIGNMENT_MODELS

    return DEVICE_OR_VM_ASSIGNMENT_MODELS


class ZabbixHostBinding(NetBoxModel):
    """Durable mapping from a NetBox Device/VM/VDC to a Zabbix host ID.

    Internal sync-identity record — not a user-facing NetBox object. There is
    intentionally no form/table/view/API surface; bindings are created and
    removed only by the host sync / delete path.

    This model is the source of truth for host identity during sync:
    it survives inherited assignments (which are transient copies), renames,
    and device deletion so the matching Zabbix host can always be found by
    hostid rather than by hostname.
    """

    zabbixserver = models.ForeignKey(
        to='nbxsync.ZabbixServer',
        on_delete=models.CASCADE,
        related_name='host_bindings',
    )
    assigned_object_type = models.ForeignKey(
        to=ContentType,
        limit_choices_to=_limit_assigned_objects,
        on_delete=models.CASCADE,
        related_name='+',
    )
    assigned_object_id = models.PositiveBigIntegerField()
    assigned_object = GenericForeignKey(
        ct_field='assigned_object_type',
        fk_field='assigned_object_id',
    )

    hostid = models.PositiveBigIntegerField()
    hostname = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Zabbix Host Binding'
        verbose_name_plural = 'Zabbix Host Bindings'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=['zabbixserver', 'assigned_object_type', 'assigned_object_id'],
                name='%(app_label)s_%(class)s_unique_binding_per_object',
                violation_error_message='A host can only be bound once to a given object on a Zabbix server.',
            ),
            models.UniqueConstraint(
                fields=['zabbixserver', 'hostid'],
                name='%(app_label)s_%(class)s_unique_hostid_per_server',
                violation_error_message='The same Zabbix host ID cannot be bound to multiple objects on a server.',
            ),
        ]

    def __str__(self):
        return f'{self.assigned_object} -> hostid:{self.hostid}@{self.zabbixserver}'
