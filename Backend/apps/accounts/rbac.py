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
    'consents.view': CLINICAL_READERS,
    # Laboratory (Module 5)
    'labs.view': CLINICAL_READERS,
    'labs.order': frozenset({T.HEPATOLOGIST, T.TRANSPLANT_SURGEON}),
    'labs.enter_result': frozenset({T.SUPER_ADMIN, T.TRANSPLANT_COORDINATOR, T.HEPATOLOGIST}),
    'labs.release': frozenset({T.HEPATOLOGIST, T.TRANSPLANT_SURGEON}),
    # Prescriptions & treatment plans (Module 6). Only doctors prescribe / manage plans.
    'prescriptions.view': CLINICAL_READERS,
    'prescriptions.prescribe': frozenset({T.HEPATOLOGIST, T.TRANSPLANT_SURGEON}),
    'treatment_plans.view': CLINICAL_READERS,
    'treatment_plans.manage': frozenset({T.HEPATOLOGIST, T.TRANSPLANT_SURGEON}),
    'drugs.manage': frozenset({T.SUPER_ADMIN, T.HEPATOLOGIST, T.TRANSPLANT_SURGEON}),
}

# Self-service capabilities of patient/donor accounts (always limited to their own records).
PATIENT_CAPABILITIES = frozenset({
    'self.patient_record',      # view own record, edit own contact details
    'self.donor_applications',  # submit / view / withdraw own applications
    'self.consents',            # view own consents
    'self.lab_results',         # view own RELEASED lab results and trends
    'self.medications',         # view own prescriptions (active + past) and treatment plans
})

EVERYONE = frozenset({'self.profile'})  # own account profile + password


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
