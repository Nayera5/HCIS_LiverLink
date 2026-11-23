"""
LiverLink role-based access control: the single source of truth for "who may do what".

Implements the approved permission matrix (D1). A capability is granted by the *effective
job title*; patients (including donors) get only their own self-service capabilities.

Rules:
- `role='clinical_staff'` or `role='admin'` WITHOUT a Staff profile has NO staff capabilities,
  until an admin assigns a job title.
- A Django superuser with no Staff profile counts as `super_admin` (the team admin account).
- A Staff profile whose job title does not match the account role grants nothing (fail closed).
- Inactive accounts get nothing.
"""

from .models import Staff, User

T = Staff.JobTitle
ALL_STAFF_TITLES = frozenset(T.values)
CLINICAL_READERS = frozenset({
    T.SUPER_ADMIN, T.TRANSPLANT_COORDINATOR, T.HEPATOLOGIST, T.RADIOLOGIST, T.TRANSPLANT_SURGEON,
})

# capability -> job titles that hold it
STAFF_CAPABILITIES = {
    'users.manage': frozenset({T.SUPER_ADMIN}),
    'audit.view': frozenset({T.SUPER_ADMIN}),
    'patients.register': frozenset({T.SUPER_ADMIN, T.TRANSPLANT_COORDINATOR}),
    'patients.view': CLINICAL_READERS | {T.BILLING_ADMIN},
    'patients.edit': frozenset({T.SUPER_ADMIN, T.TRANSPLANT_COORDINATOR}),
    'patients.change_category': frozenset({T.SUPER_ADMIN, T.TRANSPLANT_COORDINATOR, T.HEPATOLOGIST}),
    'donor_applications.submit_on_behalf': frozenset({T.TRANSPLANT_COORDINATOR}),
    'donor_applications.screen': frozenset({T.TRANSPLANT_COORDINATOR}),
    'donor_applications.view': CLINICAL_READERS,
    'consents.record': frozenset({T.TRANSPLANT_COORDINATOR, T.HEPATOLOGIST}),
    'billing.manage_services': frozenset({T.SUPER_ADMIN, T.BILLING_ADMIN}),
    'billing.view': frozenset({T.SUPER_ADMIN, T.BILLING_ADMIN}),
    'billing.create_invoice': frozenset({T.SUPER_ADMIN, T.BILLING_ADMIN}),
    'billing.record_payment': frozenset({T.SUPER_ADMIN, T.BILLING_ADMIN}),
    # Super Admin does not see consent records; consent actions are monitored via the audit log.
    'consents.view': CLINICAL_READERS - {T.SUPER_ADMIN},
    # EMR (module 4): clinical readers view; only the treating doctors write and sign.
    'emr.view': CLINICAL_READERS,
    'emr.write': frozenset({T.HEPATOLOGIST, T.TRANSPLANT_SURGEON}),
    # Scheduling (module 3): doctors manage their own working hours; super admin manages anyone's.
    'schedules.manage_own': frozenset({T.HEPATOLOGIST, T.TRANSPLANT_SURGEON, T.RADIOLOGIST}),
    'schedules.manage_all': frozenset({T.SUPER_ADMIN}),
    'appointments.view': CLINICAL_READERS,
    'appointments.book_any': frozenset({T.SUPER_ADMIN, T.TRANSPLANT_COORDINATOR}),  # on behalf of patients
    'appointments.check_in': frozenset({T.TRANSPLANT_COORDINATOR}),                 # check-in and no-show
}

# Job titles that can be the treating doctor of an encounter (holders of 'emr.write').
EMR_DOCTOR_TITLES = STAFF_CAPABILITIES['emr.write']

# Job titles that have a working schedule and can be booked for appointments.
SCHEDULABLE_TITLES = STAFF_CAPABILITIES['schedules.manage_own']

# Self-service capabilities of patient/donor accounts (always limited to their own records).
PATIENT_CAPABILITIES = frozenset({
    'self.patient_record',      # view own record, edit own contact details
    'self.donor_applications',  # submit / view / withdraw own applications
    'self.consents',            # view own consents
    'self.medical_records',     # view own released EMR records (read-only)
    'self.appointments',        # book / view / reschedule / cancel own appointments
    'self.invoices',            # view own invoices, balance & payment history
})

EVERYONE = frozenset({'self.profile', 'self.notifications'})  # own account profile + password, own notifications


def get_staff_profile(user):
    try:
        return user.staff_profile
    except Staff.DoesNotExist:
        return None


def effective_job_title(user):
    """The job title used for permission checks, or None when the user holds no staff powers."""
    if not getattr(user, 'is_authenticated', False) or not user.is_active:
        return None
    if user.role == User.Role.PATIENT:
        return None
    staff = get_staff_profile(user)
    if staff is not None:
        expected_role = Staff.role_for_job_title(staff.job_title)
        return staff.job_title if user.role == expected_role else None
    if user.is_superuser and user.role == User.Role.ADMIN:
        return T.SUPER_ADMIN
    return None


def capabilities_for(user):
    if not getattr(user, 'is_authenticated', False) or not user.is_active:
        return frozenset()
    if user.role == User.Role.PATIENT:
        return EVERYONE | PATIENT_CAPABILITIES
    title = effective_job_title(user)
    if title is None:
        return EVERYONE
    return EVERYONE | {cap for cap, titles in STAFF_CAPABILITIES.items() if title in titles}


def has_capability(user, capability):
    if capability not in STAFF_CAPABILITIES and capability not in PATIENT_CAPABILITIES \
            and capability not in EVERYONE:
        raise KeyError(f'Unknown capability: {capability}')  # typo guard
    return capability in capabilities_for(user)
