"""Access rules for the EMR API.

Roles come from User.role (admin, clinical_staff, patient) as defined in
module 1. Until accounts.User exists, Django superusers/is_staff users are
treated as clinical staff so the API stays usable during development.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

ADMIN = "admin"
CLINICAL_STAFF = "clinical_staff"
PATIENT = "patient"


def user_role(user):
    role = getattr(user, "role", None)
    if role:
        return role
    if user.is_superuser:
        return ADMIN
    if user.is_staff:
        return CLINICAL_STAFF
    return PATIENT


def is_clinical(user):
    return user_role(user) == CLINICAL_STAFF


def is_patient(user):
    return user_role(user) == PATIENT


def staff_profile(user):
    """The accounts.Staff row linked to this user, or None."""
    return getattr(user, "staff", None)


def patient_profile(user):
    """The registry.Patient row linked to this user, or None."""
    return getattr(user, "patient", None)


class EMRAccess(BasePermission):
    """
    - Clinical staff: full read/write.
    - Admin: read-only (oversight, auditing).
    - Patients/donors: read-only, own released records (filtered in the viewsets).
    """

    message = "You do not have permission to change medical records."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return is_clinical(request.user)
