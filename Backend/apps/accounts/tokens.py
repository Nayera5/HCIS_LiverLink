from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken


def revoke_all_refresh_tokens(user):
    """
    Blacklist every still-valid refresh token of `user` (used after a password change/reset and
    on deactivation). Access tokens are short-lived and JWTAuthentication also rejects inactive users.
    """
    revoked = 0
    for token in OutstandingToken.objects.filter(user=user, expires_at__gt=timezone.now()):
        _, created = BlacklistedToken.objects.get_or_create(token=token)
        revoked += created
    return revoked
