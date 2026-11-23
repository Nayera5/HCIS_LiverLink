// Human-readable descriptions of backend capabilities (apps/accounts/rbac.py).
export const CAPABILITY_DESCRIPTIONS = {
  'users.manage': 'Create staff accounts, assign job titles and activate or deactivate accounts',
  'audit.view': 'Review the audit log of who viewed or changed records',
  'patients.register': 'Register new patients and living donors',
  'patients.view': 'View patient lists and demographic profiles',
  'patients.edit': 'Edit patient demographic profiles',
  'patients.change_category': 'Change a patient’s category (liver patient, recipient, donor)',
  'donor_applications.submit_on_behalf': 'Submit donor applications on behalf of a donor',
  'donor_applications.screen': 'Screen donor applications (accept or reject)',
  'donor_applications.view': 'View donor applications',
  'labs.view': 'View lab orders, pending tests, results and trends',
  'labs.order': 'Order lab tests and cancel orders',
  'labs.enter_result': 'Enter results received from the external lab',
  'labs.release': 'Release lab results to the patient portal',
  'prescriptions.view': 'View patients’ current and past medications',
  'prescriptions.prescribe': 'Prescribe medications and stop or complete them',
  'treatment_plans.view': 'View treatment plans and plans due for review',
  'treatment_plans.manage': 'Create, edit, complete and cancel treatment plans',
  'drugs.manage': 'Add drugs to the medication catalog',
  'consents.record': 'Record signed surgery consents and withdrawals',
  'consents.view': 'View patients’ surgery consent records',
  'emr.view': 'View patients’ medical records (encounters, history, diagnoses, vitals, documents)',
  'emr.write': 'Write encounters, diagnoses, vital signs and history; sign encounters; upload and release documents',
  'reports.patients': 'View patient & donor statistics (diagnoses, categories, donor applications) and export them',
  'reports.financial': 'View financial reports (revenue by service and month, unpaid invoices) and export them',
  'reports.system_usage': 'View system usage reports (signed-in users, new accounts, appointment no-show rate)',
  'schedules.manage_own': 'Set your working days and hours so patients can book appointments',
  'schedules.manage_all': 'Set the working days and hours of any doctor',
  'appointments.view': 'View the appointment calendar of every doctor and patient',
  'appointments.book_any': 'Book, reschedule and cancel appointments on behalf of patients',
  'appointments.check_in': 'Check patients in for their appointments and mark no-shows',
  'self.appointments': 'Book, reschedule and cancel your own appointments',
  'self.patient_record': 'View your own record and update your contact details',
  'self.medical_records': 'View your own signed visits, medical history and released documents',
  'self.donor_applications': 'Apply to become a living donor and follow your application',
  'self.consents': 'View the consents you have signed',
  'services.view': 'See the list of services and their prices',
  'self.lab_results': 'View your lab results and how they change over time',
  'self.medications': 'View your medications and treatment plans',
  'self.profile': 'Manage your own account and password',
  'transplant.view': 'View transplant cases and donor evaluations',
  'transplant.manage': 'Manage transplant case workflow, donors, and checklists',
  'transplant.refer': 'Refer patients for transplant evaluation',
  'transplant.committee_decide': 'Record transplant committee decisions',
  'transplant.record_surgery': 'Schedule and record transplant surgeries',
  'transplant.view_followup': 'View post-transplant follow-up plans and visits',
  'transplant.manage_followup': 'Manage follow-up visits and recovery records',
}

// Capabilities whose pages exist today. Capabilities of later stages are added here when
// delivered, so dashboards never list unavailable features.
export const IMPLEMENTED_CAPABILITIES = new Set([
  'users.manage', 'audit.view', 'patients.register', 'patients.view', 'patients.edit', 'patients.change_category',
  'labs.view', 'labs.order', 'labs.enter_result', 'labs.release',
  'prescriptions.view', 'prescriptions.prescribe', 'treatment_plans.view', 'treatment_plans.manage', 'drugs.manage',
  'donor_applications.view', 'donor_applications.screen', 'donor_applications.submit_on_behalf',
  'consents.view', 'consents.record', 'emr.view', 'emr.write',
  'self.patient_record', 'self.donor_applications', 'self.consents', 'self.medical_records',
  'self.lab_results', 'self.medications', 'self.profile',
  'reports.patients', 'reports.financial', 'reports.system_usage', 'services.view',
  'self.patient_record', 'self.donor_applications', 'self.consents', 'self.medical_records', 'self.profile',
  'schedules.manage_own', 'schedules.manage_all', 'appointments.view', 'appointments.book_any', 'appointments.check_in',
  'self.patient_record', 'self.appointments', 'self.donor_applications', 'self.consents', 'self.medical_records', 'self.profile',
  'transplant.view', 'transplant.manage', 'transplant.refer', 'transplant.committee_decide',
  'transplant.record_surgery', 'transplant.view_followup', 'transplant.manage_followup',
])

export function describeCapabilities(capabilities = []) {
  return capabilities
    .filter((cap) => cap !== 'self.profile' && IMPLEMENTED_CAPABILITIES.has(cap) && CAPABILITY_DESCRIPTIONS[cap])
    .map((cap) => ({ key: cap, text: CAPABILITY_DESCRIPTIONS[cap] }))
}
