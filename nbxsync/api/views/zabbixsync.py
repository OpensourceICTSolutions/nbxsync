from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django_rq import get_queue
from drf_spectacular.utils import extend_schema

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from nbxsync.constants.assignment_type_to_field import OBJECT_TYPE_MODEL_MAP


class ZabbixSyncViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @extend_schema(exclude=True)
    def create(self, request, **kwargs):
        obj_type = (request.data.get('obj_type') or '').strip().lower()
        obj_id = request.data.get('obj_id')

        if not obj_type:
            raise ValidationError("Should specify 'obj_type'")
        if not obj_id:
            raise ValidationError("Should specify 'obj_id'")

        if obj_type not in OBJECT_TYPE_MODEL_MAP:
            raise ValidationError(f"Field obj_type '{obj_type}' is invalid, should be one of 'device', 'virtualmachine', or 'virtualdevicecontext'")

        try:
            obj_id = int(obj_id)
        except (TypeError, ValueError):
            raise ValidationError('obj_id must be an integer')

        Model = OBJECT_TYPE_MODEL_MAP[obj_type]
        instance = get_object_or_404(Model, pk=obj_id)

        content_type = ContentType.objects.get_for_model(instance)
        queue = get_queue('low')
        queue.enqueue_job(
            queue.create_job(
                func='nbxsync.worker.synchost',
                args=[content_type.app_label, content_type.model, instance.pk],
                timeout=9000,
            )
        )

        return Response({'count': 1, 'results': [{'scheduled': True}]}, status=202)
