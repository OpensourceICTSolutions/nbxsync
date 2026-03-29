from django_rq import get_queue
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from django.apps import apps
from django.shortcuts import get_object_or_404

from nbxsync.api.serializers import ZabbixHostInterfaceSerializer
from nbxsync.models import ZabbixHostInterface
from nbxsync.constants import OBJECT_TYPE_MODEL_MAP


class ZabbixSyncViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ZabbixHostInterfaceSerializer

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

        queue = get_queue('low')
        queue.enqueue_job(queue.create_job(func='nbxsync.worker.synchost', args=[instance], timeout=9000))

        return Response({'count': 1, 'results': [{'scheduled': True}]}, status=202)
