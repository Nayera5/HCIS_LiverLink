"""
Notifications (spec §14 and entity dictionary §4.42).

Keeps users informed, in-app (and by email, once email sending is configured).

Deviations from the spec (agreed for this first pass):
- Email is not implemented yet: no SMTP is configured anywhere in the project. The `channel`
  field is kept (matching the spec) but restricted to `in_app` only for now.
- No other module (scheduling, labs, radiology, transplant) exists yet to raise real
  notifications automatically. `notify()` is the integration point those modules will call once
  built; for now, notifications are created manually through the Django admin.
"""
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Notification(models.Model):
    """An in-app message sent to a user (§4.42)."""

    class Type(models.TextChoices):
        APPOINTMENT_REMINDER = 'appointment_reminder', 'Appointment reminder'
        RESULT_READY = 'result_ready', 'Result ready'
        CASE_UPDATE = 'case_update', 'Case update'
        PENDING_TASK = 'pending_task', 'Pending task'
        FOLLOW_UP_REMINDER = 'follow_up_reminder', 'Follow-up reminder'

    class Channel(models.TextChoices):
        IN_APP = 'in_app', 'In-app'
        # EMAIL = 'email', 'Email'  # re-enable once SMTP is configured (spec §4.42).

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=30, choices=Type.choices)
    title = models.CharField(max_length=150, blank=True)
    message = models.TextField()
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.IN_APP)
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-sent_at', '-id']
        indexes = [
            models.Index(fields=['user', 'is_read'], name='notif_user_unread_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(type__in=[
                    'appointment_reminder', 'result_ready', 'case_update', 'pending_task',
                    'follow_up_reminder',
                ]),
                name='notif_type_valid'),
            models.CheckConstraint(condition=Q(channel__in=['in_app']), name='notif_channel_valid'),
        ]

    def __str__(self):
        return f'{self.get_type_display()} to {self.user.username} ({"read" if self.is_read else "unread"})'


def notify(user, notif_type, message, *, title=''):
    """
    Create a notification for `user`. The integration point future modules (scheduling, labs,
    radiology, transplant) will call once built, e.g. `notify(patient.user, Notification.Type.
    APPOINTMENT_REMINDER, 'Your CT scan is tomorrow at 9:00.')`.
    """
    return Notification.objects.create(user=user, type=notif_type, title=title, message=message)
