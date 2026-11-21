"""
Helper for writing audit entries from API views (spec §4.4: every view, create, update and delete
on clinical data writes a row).

Only *who / what / which row / when / from where* is stored: never field values, search terms,
passwords or tokens.
"""
from .models import AuditLog


def client_ip(request):
    """The connecting client's IP (REMOTE_ADDR). Proxy headers are not trusted here."""
    return request.META.get('REMOTE_ADDR') or None


def audit(request, action, entity_type, *, entity_id=None, patient=None, user=None, actor=''):
    """
    Append one audit entry for `request`. `user` defaults to the authenticated request user;
    pass `user` explicitly when the account was just created (self-registration).
    """
    return AuditLog.record(
        action,
        entity_type,
        user=user if user is not None else request.user,
        actor=actor,
        entity_id=entity_id,
        patient=patient,
        ip_address=client_ip(request),
    )
