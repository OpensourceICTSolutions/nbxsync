from django.db import models
from django.utils.timezone import now

__all__ = ('SyncInfoModel',)


class SyncInfoModel(models.Model):
    last_sync = models.DateTimeField(null=True, blank=True)
    last_sync_state = models.BooleanField(default=False)
    last_sync_message = models.CharField(max_length=3000, blank=False, default='Never synced')

    class Meta:
        abstract = True

    def update_sync_info(self, success: bool, message: str = ''):
        """
        Update the sync fields in the model.

        Args:
            success (bool): Whether the sync was successful.
            message (str): Optional message to describe the sync outcome.
        """
        if success and message == '':
            message = 'Synchronization successful'

        if not success and message == '':
            message = 'Synchronization failed'

        self.last_sync = now()
        self.last_sync_state = success
        self.last_sync_message = message
        self.save(update_fields=['last_sync', 'last_sync_state', 'last_sync_message'])
