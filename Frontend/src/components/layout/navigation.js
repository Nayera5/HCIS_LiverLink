// Sidebar navigation. Items are shown only when the user holds `capability` (if given; a list
// means any of them); the backend enforces the same rules. Later stages add their pages here.
import { REPORT_CAPABILITIES } from '../../pages/Reports/reportDisplay'
import {
  CheckCircleIcon, ClipboardIcon, ClockIcon, CreditCardIcon, FlaskIcon, GridIcon, HeartPulseIcon, PillIcon,
  ReceiptIcon, ShieldIcon, TargetIcon, UserIcon, UserPlusIcon, UsersIcon,
  BarChartIcon, CalendarIcon, CheckCircleIcon, ClipboardIcon, ClockIcon, CreditCardIcon,
  GridIcon, HeartPulseIcon, ReceiptIcon, ShieldIcon, UserIcon, UserPlusIcon, UsersIcon,
} from '../ui/icons'

export const NAV_SECTIONS = [
  {
    label: 'Overview',
    items: [{ to: '/', label: 'Dashboard', icon: GridIcon, end: true }],
  },
  {
    label: 'Clinical',
    items: [
      { to: '/patients', label: 'Patients', icon: ClipboardIcon, capability: 'patients.view' },
      { to: '/lab/orders', label: 'Lab orders', icon: FlaskIcon, capability: 'labs.view' },
      { to: '/lab/pending', label: 'Pending tests', icon: ClockIcon, capability: 'labs.view' },
      { to: '/rx/reviews', label: 'Plan reviews due', icon: TargetIcon, capability: 'treatment_plans.view' },
      { to: '/appointments', label: 'Appointments', icon: CalendarIcon, capability: 'appointments.view' },
      { to: '/schedule', label: 'My schedule', icon: ClockIcon, capability: 'schedules.manage_own' },
      { to: '/donor-applications', label: 'Donor applications', icon: UserPlusIcon, capability: 'donor_applications.view' },
      { to: '/transplant', label: 'Transplant cases', icon: HeartPulseIcon, capability: 'transplant.view' },
      { to: '/followup', label: 'Follow-up', icon: CheckCircleIcon, capability: 'transplant.view_followup' },
    ],
  },
  {
    label: 'Billing',
    items: [
      { to: '/billing/invoices', label: 'Invoices', icon: ReceiptIcon, capability: 'billing.view' },
      { to: '/billing/services', label: 'Service catalog', icon: CreditCardIcon, capability: 'billing.view' },
    ],
  },
  {
    label: 'Analytics',
    // Shown when the user may open at least one report.
    items: [{ to: '/reports', label: 'Reports', icon: BarChartIcon, capability: REPORT_CAPABILITIES }],
  },
  {
    label: 'My health',
    items: [
      { to: '/my-record', label: 'My health record', icon: HeartPulseIcon, capability: 'self.patient_record' },
      { to: '/my-lab-orders', label: 'My lab orders', icon: ClockIcon, capability: 'self.lab_results' },
      { to: '/my-results', label: 'My lab results', icon: FlaskIcon, capability: 'self.lab_results' },
      { to: '/my-medications', label: 'My medications', icon: PillIcon, capability: 'self.medications' },
      { to: '/my-treatment-plans', label: 'My treatment plans', icon: TargetIcon, capability: 'self.medications' },
      { to: '/my-appointments', label: 'My appointments', icon: CalendarIcon, capability: 'self.appointments' },
      { to: '/my-medical-record', label: 'My medical record', icon: ClipboardIcon, capability: 'self.medical_records' },
      { to: '/my-donor-applications', label: 'My donor applications', icon: UserPlusIcon, capability: 'self.donor_applications' },
      { to: '/my-invoices', label: 'My invoices', icon: ReceiptIcon, capability: 'self.invoices' },
      { to: '/my-consents', label: 'My consents', icon: CheckCircleIcon, capability: 'self.consents' },
    ],
  },
  {
    label: 'Administration',
    items: [
      { to: '/admin/users', label: 'Users & access', icon: UsersIcon, capability: 'users.manage' },
      { to: '/schedule', label: 'Doctor schedules', icon: ClockIcon, capability: 'schedules.manage_all' },
      { to: '/admin/audit-logs', label: 'Audit logs', icon: ShieldIcon, capability: 'audit.view' },
    ],
  },
  {
    label: 'Account',
    items: [{ to: '/profile', label: 'My profile', icon: UserIcon }],
  },
]

/** Sections filtered for the user; empty sections are dropped. */
export function navigationFor(can) {
  return NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => !item.capability
      || (Array.isArray(item.capability) ? item.capability.some(can) : can(item.capability))),
  })).filter((section) => section.items.length > 0)
}

/** Primary top-bar action per role (design reference: "+ New encounter"). */
export function primaryActionFor(can) {
  if (can('users.manage')) return { to: '/admin/users/new', label: 'New staff account' }
  if (can('patients.register')) return { to: '/patients/new', label: 'Register patient' }
  if (can('billing.create_invoice')) return { to: '/billing/invoices/new', label: 'New invoice' }
  if (can('self.appointments')) return { to: '/my-appointments/new', label: 'Book appointment' }
  return null
}
