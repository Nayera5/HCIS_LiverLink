"""
Access rules for the EMR API, built on the module 1 permission matrix (apps/accounts/rbac.py):

    emr.view              read all patients' records    super_admin, coordinator, hepatologist,
                                                        radiologist, transplant_surgeon
    emr.write             create / edit / sign / release hepatologist, transplant_surgeon
    self.medical_records  own released records only      patients and donors (read-only)

Billing Admin and staff without a job title get nothing.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.rbac import get_staff_profile, has_capability
from apps.registry.models import Patient


def can_view_all(user):
    return has_capability(user, 'emr.view')


def can_write(user):
    return has_capability(user, 'emr.write')


def is_portal_user(user):
    """A patient/donor account: sees only its own released records."""
    return has_capability(user, 'self.medical_records')


def staff_profile(user):
    """The accounts.Staff row linked to this user, or None."""
    return get_staff_profile(user)


def patient_profile(user):
    """The registry.Patient row linked to this user, or None."""
    return Patient.objects.filter(user=user).first()


class EMRAccess(BasePermission):
    message = 'You do not have permission to access medical records.'

    def has_permission(self, request, view):
        user = request.user
        if request.method in SAFE_METHODS:
            return can_view_all(user) or is_portal_user(user)
        return can_write(user)
