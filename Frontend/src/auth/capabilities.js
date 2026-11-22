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
  'consents.record': 'Record signed consents and withdrawals',
  'consents.view': 'View patients’ consent records',
  'labs.view': 'View lab orders, pending tests, results and trends',
  'labs.order': 'Order lab tests and cancel orders',
  'labs.enter_result': 'Enter results received from the external lab',
  'labs.release': 'Release lab results to the patient portal',
  'prescriptions.view': 'View patients’ current and past medications',
  'prescriptions.prescribe': 'Prescribe medications and stop or complete them',
  'treatment_plans.view': 'View treatment plans and plans due for review',
  'treatment_plans.manage': 'Create, edit, complete and cancel treatment plans',
  'drugs.manage': 'Add drugs to the medication catalog',
  'self.patient_record': 'View your own record and update your contact details',
  'self.donor_applications': 'Apply to become a living donor and follow your application',
  'self.consents': 'View the consents you have signed',
  'self.lab_results': 'View your lab results and how they change over time',
  'self.medications': 'View your medications and treatment plans',
  'self.profile': 'Manage your own account and password',
}

// Capabilities whose pages exist today. Others (donor applications, consents) are
// added here when their stage is delivered, so dashboards never list unavailable features.
export const IMPLEMENTED_CAPABILITIES = new Set([
  'users.manage', 'audit.view', 'patients.register', 'patients.view', 'patients.edit', 'patients.change_category',
  'labs.view', 'labs.order', 'labs.enter_result', 'labs.release',
  'prescriptions.view', 'prescriptions.prescribe', 'treatment_plans.view', 'treatment_plans.manage', 'drugs.manage',
  'self.patient_record', 'self.lab_results', 'self.medications', 'self.profile',
])

export function describeCapabilities(capabilities = []) {
  return capabilities
    .filter((cap) => cap !== 'self.profile' && IMPLEMENTED_CAPABILITIES.has(cap) && CAPABILITY_DESCRIPTIONS[cap])
    .map((cap) => ({ key: cap, text: CAPABILITY_DESCRIPTIONS[cap] }))
}
