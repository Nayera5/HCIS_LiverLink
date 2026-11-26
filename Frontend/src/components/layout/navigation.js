// Sidebar navigation. Items are shown only when the user holds `capability` (if given; a list
// means any of them); the backend enforces the same rules. Later stages add their pages here.
import { REPORT_CAPABILITIES } from '../../pages/Reports/reportDisplay'
import {
  CheckCircleIcon,
  ClipboardIcon,
  ClockIcon,
  CreditCardIcon,
  FlaskIcon,
  GridIcon,
  HeartPulseIcon,
  MailIcon,
  PillIcon,
  ReceiptIcon,
  ScanIcon,
  ShieldIcon,
  TargetIcon,
  UserIcon,
  UserPlusIcon,
  UsersIcon,
  BarChartIcon,
  CalendarIcon,
} from '../ui/icons'
import { filterNavigationSections } from './navigationRules'

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
      { to: '/imaging/orders', label: 'Imaging orders', icon: ScanIcon, capability: 'imaging.view' },
      { to: '/imaging/slots', label: 'Scan slots', icon: ClockIcon, capability: 'imaging.manage' },
      { to: '/rx/reviews', label: 'Plan reviews due', icon: TargetIcon, capability: 'treatment_plans.view' },
      {
        to: '/appointments', label: 'Appointments', icon: CalendarIcon, capability: 'appointments.view',
        excludeJobTitles: ['radiologist'],
      },
      { to: '/schedule', label: 'My schedule', icon: ClockIcon, capability: 'schedules.manage_own' },
      {
        to: '/donor-applications', label: 'Donor applications', icon: UserPlusIcon, capability: 'donor_applications.view',
        excludeJobTitles: ['radiologist'],
      },
      {
        to: '/transplant', label: 'Transplant cases', icon: HeartPulseIcon, capability: 'transplant.view',
        excludeJobTitles: ['radiologist'],
      },
      { to: '/followup', label: 'Follow-up', icon: CheckCircleIcon, capability: 'transplant.view_followup' },
    ],
  },
  {
    label: 'My health',
    items: [
      { to: '/my-medical-record', label: 'Medical Record', icon: ClipboardIcon, capability: 'self.medical_records' },
      { to: '/my-results', label: 'Lab & Test Results', icon: FlaskIcon, capability: 'self.lab_results' },
      { to: '/my-medications', label: 'Medications', icon: PillIcon, capability: 'self.medications' },
      { to: '/my-treatment-plans', label: 'Treatment Plans', icon: TargetIcon, capability: 'self.medications' },
      { to: '/my-appointments', label: 'Appointments', icon: CalendarIcon, capability: 'self.appointments' },
      { to: '/my-followup', label: 'Follow-up', icon: CheckCircleIcon, capability: 'self.followup' },
      { to: '/my-imaging', label: 'Scans', icon: ScanIcon, capability: 'self.imaging_orders' },
    ],
  },
  {
    label: 'Donation & consents',
    items: [
      { to: '/my-donor-applications', label: 'Donor Applications', icon: UserPlusIcon, capability: 'self.donor_applications' },
      { to: '/my-consents', label: 'Consents', icon: CheckCircleIcon, capability: 'self.consents' },
    ],
  },
  {
    label: 'Billing',
    items: [
      { to: '/billing/invoices', label: 'Invoices', icon: ReceiptIcon, capability: 'billing.view' },
      { to: '/billing/services', label: 'Service catalog', icon: CreditCardIcon, capability: 'billing.view' },
      { to: '/my-invoices', label: 'Invoices', icon: ReceiptIcon, capability: 'self.invoices' },
      // Read-only list for clinical staff and patients (admins have the Service catalog above).
      { to: '/services', label: 'Services & prices', icon: CreditCardIcon, capability: 'services.view' },
    ],
  },
  {
    label: 'Analytics',
    // Shown when the user may open at least one report.
    items: [{ to: '/reports', label: 'Reports', icon: BarChartIcon, capability: REPORT_CAPABILITIES }],
  },
  {
    label: 'Administration',
    items: [
      { to: '/admin/users', label: 'Users & access', icon: UsersIcon, capability: 'users.manage' },
      { to: '/schedule', label: 'Doctor schedules', icon: ClockIcon, capability: 'schedules.manage_all' },
      { to: '/admin/audit-logs', label: 'Audit logs', icon: ShieldIcon, capability: 'audit.view' },
      { to: '/admin/hl7-messages', label: 'HL7 messages', icon: MailIcon, capability: 'hl7.monitor' },
    ],
  },
  {
    label: 'Account',
    items: [{ to: '/profile', label: 'My profile', icon: UserIcon }],
  },
]

/** Sections filtered for the user; empty sections are dropped. */
export function navigationFor(can, jobTitle) {
  return filterNavigationSections(NAV_SECTIONS, can, jobTitle)
}

/** Primary top-bar action per role (design reference: "+ New encounter"). */
export function primaryActionFor(can) {
  if (can('users.manage')) return { to: '/admin/users/new', label: 'New staff account' }
  if (can('patients.register')) return { to: '/patients/new', label: 'Register patient' }
  if (can('billing.create_invoice')) return { to: '/billing/invoices/new', label: 'New invoice' }
  if (can('self.appointments')) return { to: '/my-appointments/new', label: 'Book appointment' }
  return null
}
