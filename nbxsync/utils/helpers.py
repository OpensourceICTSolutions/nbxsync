from django.contrib.contenttypes.models import ContentType

from nbxsync.api.serializers import ZabbixMacroSerializer, ZabbixTemplateSerializer
from nbxsync.models import ZabbixMacro, ZabbixTemplate


def create_or_update_zabbixtemplate(template, zabbixserver):
    existing = ZabbixTemplate.objects.filter(templateid=template['templateid'], zabbixserver_id=zabbixserver.id).first()

    if existing:
        # Update the existing macro if any values differ
        serializer = ZabbixTemplateSerializer(existing, data=template, partial=True)
        if serializer.is_valid():
            updated_instance = serializer.save()
            return updated_instance
        else:
            return existing

    template['zabbixserver'] = zabbixserver.id
    template['zabbixserver_id'] = zabbixserver.id

    serializer = ZabbixTemplateSerializer(data=template)
    if serializer.is_valid():
        return serializer.save()
    else:
        return None


def create_or_update_zabbixmacro(macro, zabbixtemplate):
    content_type = ContentType.objects.get_for_model(zabbixtemplate)
    existing = ZabbixMacro.objects.filter(hostmacroid=macro['hostmacroid'], assigned_object_type=content_type, assigned_object_id=zabbixtemplate.id).first()

    if existing:
        # Update the existing macro if any values differ
        serializer = ZabbixMacroSerializer(existing, data=macro, partial=True)
        if serializer.is_valid():
            updated_instance = serializer.save()
            return updated_instance
        else:
            return existing

    macro['assigned_object_type'] = f'{content_type.app_label}.{content_type.model}'
    macro['assigned_object_id'] = zabbixtemplate.id

    serializer = ZabbixMacroSerializer(data=macro)
    if serializer.is_valid():
        return serializer.save()
    else:
        return None
