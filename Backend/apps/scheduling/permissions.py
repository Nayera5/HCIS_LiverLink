"""
Access rules for the scheduling API, built on the module 1 permission matrix (apps/accounts/rbac.py):

    appointments.view      see all appointments and schedules   clinical readers
    appointments.book_any  book / reschedule / cancel for anyone super_admin, coordinator
    appointments.check_in  check-in and no-show                  coordinator
    schedules.manage_own   manage own working schedule           hepatologist, surgeon, radiologist
    schedules.manage_all   manage any doctor's schedule          super_admin
    self.appointments      book / view / reschedule / cancel own patients and donors

Completing an appointment is allowed to its doctor and to the coordinator (checked in views.py).
Billing Admin and staff without a job title get nothing.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.rbac import has_capability


def can_view_all(user):
    return has_capability(user, 'appointments.view')


def can_book_any(user):
    return has_capability(user, 'appointments.book_any')


def is_portal_user(user):
    """A patient/donor account: sees and books only its own appointments."""
    return has_capability(user, 'self.appointments')


def can_manage_schedules(user):
    return has_capability(user, 'schedules.manage_own') or has_capability(user, 'schedules.manage_all')


class AppointmentAccess(BasePermission):
    message = 'You do not have permission to access appointments.'

    def has_permission(self, request, view):
        user = request.user
        if request.method in SAFE_METHODS:
            return can_view_all(user) or is_portal_user(user)
        # Writes: bookers, portal users (own only, enforced in the view), and the status
        # actions (check-in / no-show / complete) whose rules are checked in the view.
        return can_book_any(user) or is_portal_user(user) or can_view_all(user)


class ScheduleAccess(BasePermission):
    """Everyone who can book or view appointments can read schedules and free slots."""

    message = 'You do not have permission to manage doctor schedules.'

    def has_permission(self, request, view):
        user = request.user
        if request.method in SAFE_METHODS:
            return can_view_all(user) or is_portal_user(user)
        return can_manage_schedules(user)
