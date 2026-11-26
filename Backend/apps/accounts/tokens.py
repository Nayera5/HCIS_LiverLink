from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .audit import audit
from .models import AuditLog, User


class AuditedTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Issue JWTs while recording login outcomes without retaining credentials."""

    def validate(self, attrs):
        request = self.context['request']
        attempted_username = attrs.get(User.USERNAME_FIELD, '')
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            attempted_user = User.objects.filter(username=attempted_username).first()
            audit(
                request,
                AuditLog.Action.LOGIN,
                'accounts.user',
                user=attempted_user,
                actor=attempted_username,
                entity_id=attempted_user.pk if attempted_user else None,
                outcome=AuditLog.Outcome.FAILURE,
            )
            raise

        user = self.user
        audit(
            request,
            AuditLog.Action.LOGIN,
            'accounts.user',
            user=user,
            entity_id=user.pk,
            outcome=AuditLog.Outcome.SUCCESS,
        )
        return data


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
