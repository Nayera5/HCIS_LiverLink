from rest_framework.permissions import BasePermission

from .rbac import has_capability


def HasCapability(*capabilities):
    """
    DRF permission class factory: the user must hold ANY of the given capabilities.

        permission_classes = [HasCapability('users.manage')]
    """
    for cap in capabilities:  # fail fast on typos at import time
        has_capability(_NoUser, cap)

    class _HasCapability(BasePermission):
        message = 'You do not have permission to perform this action.'

        def has_permission(self, request, view):
            return any(has_capability(request.user, cap) for cap in capabilities)

    _HasCapability.__name__ = f'HasCapability({", ".join(capabilities)})'
    return _HasCapability


class _NoUser:
    is_authenticated = False
    is_active = False
