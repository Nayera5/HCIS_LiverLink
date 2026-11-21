// Sidebar navigation. Items are shown only when the user holds `capability` (if given);
// the backend enforces the same rules. Later stages add their pages here.
import { ClipboardIcon, GridIcon, HeartPulseIcon, ShieldIcon, UserIcon, UserPlusIcon, UsersIcon } from '../ui/icons'

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
    label: 'My health',
    items: [
      { to: '/my-record', label: 'My health record', icon: HeartPulseIcon, capability: 'self.patient_record' },
      { to: '/my-donor-applications', label: 'My donor applications', icon: UserPlusIcon,
        capability: 'self.donor_applications' },
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
  return null
}
