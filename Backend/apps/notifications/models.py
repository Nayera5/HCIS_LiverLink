"""
Notifications (spec §14 and entity dictionary §4.42).

Keeps users informed, in-app (and by email, once email sending is configured).

Where notifications come from (see apps.notifications.events and .tasks):
- appointment_reminder / follow_up_reminder: the periodic `check_due_reminders` Celery task.
- result_ready: lab orders (doctor when all results are in, patient when they are released).
- case_update: every transplant case stage change (TransplantCase.transition_to).
- pending_task: the periodic task tells the coordinator about open cases with pending
  required checklist items (missing tests or documents), at most once a day per case.

Deviations from the spec:
- Email is not sent yet: the `channel` field is kept (matching the spec) but restricted to
  `in_app` for now.
- Addition: `related_type` / `related_id` name the record a notification is about (e.g.
  'scheduling.appointment', 42). They stop the periodic task from sending the same reminder twice.
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
    related_type = models.CharField(
        max_length=50, blank=True, help_text="Record the notification is about, as 'app_label.model'.")
    related_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-sent_at', '-id']
        indexes = [
            models.Index(fields=['user', 'is_read'], name='notif_user_unread_idx'),
            models.Index(fields=['type', 'related_type', 'related_id'], name='notif_related_idx'),
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


def related_key(obj):
    """('app_label.model', pk) for a model instance, or ('', None)."""
    if obj is None:
        return '', None
    return obj._meta.label_lower, obj.pk


def notify(user, notif_type, message, *, title='', related=None):
    """
    Create an in-app notification for `user`. Does nothing (returns None) when there is nobody to
    tell: no user (e.g. a patient without a portal account) or a deactivated account.
    `related` is the model instance the notification is about.
    """
    if user is None or not user.is_active:
        return None
    related_type, related_id = related_key(related)
    return Notification.objects.create(user=user, type=notif_type, title=title, message=message,
                                       related_type=related_type, related_id=related_id)


def already_notified(user, notif_type, related, *, since=None):
    """Whether `user` already got a `notif_type` notification about `related` (optionally since a time)."""
    related_type, related_id = related_key(related)
    qs = Notification.objects.filter(user=user, type=notif_type, related_type=related_type, related_id=related_id)
    if since is not None:
        qs = qs.filter(sent_at__gte=since)
    return qs.exists()
