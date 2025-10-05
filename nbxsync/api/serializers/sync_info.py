from rest_framework import serializers

__all__ = ('SyncInfoSerializerMixin',)


class SyncInfoSerializerMixin(serializers.Serializer):
    last_sync = serializers.DateTimeField(read_only=True)
    last_sync_state = serializers.BooleanField(read_only=True)
    last_sync_message = serializers.CharField(read_only=True)
