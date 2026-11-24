"""
Email copies of notifications (spec §14 "in-app and by email").

notify() calls queue_email() for every new in-app notification. If its type is in
settings.NOTIFICATION_EMAIL_TYPES and the user has an email address, the email is sent once the
surrounding transaction commits (nothing is emailed for a change that was rolled back), on a
background thread so the request is not slowed down by the mail server. A successful send is
recorded as a Notification row with channel='email'. A failed send is logged and does not affect
the in-app notification.
"""
import logging
import threading

from django.conf import settings
from django.core.mail import send_mail
from django.db import close_old_connections, transaction

from .models import Notification

logger = logging.getLogger(__name__)


def wants_email(notification):
    return notification.type in settings.NOTIFICATION_EMAIL_TYPES and bool(notification.user.email)


def render(notification):
    """(subject, body) of the email for an in-app notification."""
    user = notification.user
    title = notification.title or notification.get_type_display()
    link = f"{settings.FRONTEND_URL.rstrip('/')}/notifications"
    body = (
        f'Hello {user.get_full_name() or user.username},\n\n'
        f'{notification.message}\n\n'
        f'Open LiverLink to see all your notifications: {link}\n\n'
        '— LiverLink\n'
        'You receive this email because you have a LiverLink account.\n'
    )
    return f'LiverLink: {title}', body


def send_now(notification_id):
    """Send the email for one in-app notification and record it. Returns True when sent."""
    notification = Notification.objects.select_related('user').filter(pk=notification_id).first()
    if notification is None or not wants_email(notification):
        return False
    subject, body = render(notification)
    try:
        send_mail(subject, body, from_email=None, recipient_list=[notification.user.email])
    except Exception:
        logger.exception('Email for notification %s to user %s failed', notification.pk, notification.user_id)
        return False
    Notification.objects.create(
        user=notification.user, type=notification.type, title=notification.title,
        message=notification.message, channel=Notification.Channel.EMAIL, is_read=True,
        related_type=notification.related_type, related_id=notification.related_id)
    return True


def _send_in_background(notification_id):
    try:
        send_now(notification_id)
    finally:
        close_old_connections()  # this thread opened its own database connection


def queue_email(notification):
    """Email `notification` after the current transaction commits, when its type is emailed."""
    if notification.channel != Notification.Channel.IN_APP or not wants_email(notification):
        return
    pk = notification.pk
    if settings.NOTIFICATION_EMAIL_ASYNC:
        transaction.on_commit(lambda: threading.Thread(
            target=_send_in_background, args=(pk,), daemon=True, name=f'notification-email-{pk}').start())
    else:
        transaction.on_commit(lambda: send_now(pk))
