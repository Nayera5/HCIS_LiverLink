// Sidebar navigation. Items are shown only when the user holds `capability` (if given);
// the backend enforces the same rules. Later stages add their pages here.
import {
  ClipboardIcon, CreditCardIcon, GridIcon, HeartPulseIcon, ReceiptIcon, ShieldIcon, UserIcon, UserPlusIcon, UsersIcon, CheckCircleIcon,
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
      { to: '/donor-applications', label: 'Donor applications', icon: UserPlusIcon, capability: 'donor_applications.view' },
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
    label: 'My health',
    items: [
      { to: '/my-record', label: 'My health record', icon: HeartPulseIcon, capability: 'self.patient_record' },
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
    items: section.items.filter((item) => !item.capability || can(item.capability)),
  })).filter((section) => section.items.length > 0)
}

/** Primary top-bar action per role (design reference: "+ New encounter"). */
export function primaryActionFor(can) {
  if (can('users.manage')) return { to: '/admin/users/new', label: 'New staff account' }
  if (can('patients.register')) return { to: '/patients/new', label: 'Register patient' }
  if (can('billing.create_invoice')) return { to: '/billing/invoices/new', label: 'New invoice' }
  return null
}
