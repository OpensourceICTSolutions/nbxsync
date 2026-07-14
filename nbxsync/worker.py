import logging

from django.contrib.contenttypes.models import ContentType
from django_rq import job

from nbxsync.jobs import *

logger = logging.getLogger('worker')


@job('low')
def synchost(app_label, model_name, object_id):
    content_type = ContentType.objects.get_by_natural_key(app_label, model_name)
    model = content_type.model_class()
    if model is None:
        logger.warning('Cannot sync removed content type %s.%s', app_label, model_name)
        return

    try:
        instance = model.objects.get(pk=object_id)
    except model.DoesNotExist:
        logger.info('Skipping deleted sync target %s.%s:%s', app_label, model_name, object_id)
        return

    worker = SyncHostJob(instance=instance)
    worker.run()


@job('low')
def deletehost(instance):
    worker = DeleteHostJob(instance=instance)
    worker.run()


@job('low')
def syncproxygroup(instance):
    worker = SyncProxyGroupJob(instance=instance)
    worker.run()


@job('low')
def syncproxy(instance):
    worker = SyncProxyJob(instance=instance)
    worker.run()


@job('low')
def synctemplates(instance):
    worker = SyncTemplatesJob(instance=instance)
    worker.run()


@job('low')
def syncmaintenance(instance):
    worker = SyncMaintenceJob(instance=instance)
    worker.run()


@job('low')
def deletemaintenance(instance):
    worker = DeleteMaintenanceJob(instance=instance)
    worker.run()


@job('low')
def propagate_configgroup_assignment(assignment_pk):
    PropagateConfigGroupAssignmentJob(assignment_pk=assignment_pk).run()


@job('low')
def delete_configgroup_assignment_children(configgroup_pk, assigned_object_type_pk, assigned_object_id):
    DeleteConfigGroupAssignmentChildrenJob(configgroup_pk=configgroup_pk, assigned_object_type_pk=assigned_object_type_pk, assigned_object_id=assigned_object_id).run()


@job('low')
def propagate_server_assignment(assignment_pk):
    PropagateServerAssignmentJob(assignment_pk=assignment_pk).run()


@job('low')
def delete_server_assignment_clones(configgroup_pk, assigned_object_type_pk, zabbixserver_pk):
    DeleteServerAssignmentClonesJob(configgroup_pk=configgroup_pk, assigned_object_type_pk=assigned_object_type_pk, zabbixserver_pk=zabbixserver_pk).run()


@job('low')
def propagate_template_assignment(assignment_pk):
    PropagateTemplateAssignmentJob(assignment_pk=assignment_pk).run()


@job('low')
def delete_template_assignment_clones(configgroup_pk, assigned_object_type_pk, zabbixtemplate_pk):
    DeleteTemplateAssignmentClonesJob(configgroup_pk=configgroup_pk, assigned_object_type_pk=assigned_object_type_pk, zabbixtemplate_pk=zabbixtemplate_pk).run()


@job('low')
def propagate_tag_assignment(assignment_pk):
    PropagateTagAssignmentJob(assignment_pk=assignment_pk).run()


@job('low')
def delete_tag_assignment_clones(configgroup_pk, zabbixtag_pk):
    DeleteTagAssignmentClonesJob(configgroup_pk=configgroup_pk, zabbixtag_pk=zabbixtag_pk).run()


@job('low')
def propagate_hostgroup_assignment(assignment_pk):
    PropagateHostGroupAssignmentJob(assignment_pk=assignment_pk).run()


@job('low')
def delete_hostgroup_assignment_clones(configgroup_pk):
    DeleteHostGroupAssignmentClonesJob(configgroup_pk=configgroup_pk).run()


@job('low')
def propagate_macro_assignment_create(assignment_pk):
    PropagateMacroAssignmentCreateJob(assignment_pk=assignment_pk).run()


@job('low')
def propagate_macro_assignment_update(assignment_pk):
    PropagateMacroAssignmentUpdateJob(assignment_pk=assignment_pk).run()
