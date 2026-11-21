// Audit log viewer: filter handling and display helpers (no React, so `npm test` can import it).
// Mirrors the backend contract of GET /api/audit-logs/ (apps/accounts/views.py: AuditLogListView).

export const ACTION_LABELS = {
  profile_view: 'Profile view',
  view: 'View',
  export: 'Export',
  create: 'Create',
  update: 'Update',
  category_change: 'Category change',
  activate: 'Activate',
  deactivate: 'Deactivate',
  status_change: 'Status change',
  withdraw: 'Withdraw',
  delete: 'Delete',
  login: 'Login',
  logout: 'Logout',
}

// Read actions (backend AuditLog.READ_ACTIONS); everything else is a write or session event.
export const READ_ACTIONS = new Set(['view', 'profile_view', 'export'])

export const ACTION_OPTIONS = [
  { group: 'Reads', options: ['profile_view', 'view', 'export'] },
  { group: 'Writes', options: ['create', 'update', 'category_change', 'status_change', 'withdraw', 'activate', 'deactivate', 'delete'] },
  { group: 'Sessions', options: ['login', 'logout'] },
].map(({ group, options }) => ({
  group,
  options: options.map((value) => ({ value, label: ACTION_LABELS[value] })),
}))

// Type filter. The viewer opens on writes; reads (e.g. patient profile access) are one click away.
export const KIND_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'read', label: 'Reads' },
  { value: 'write', label: 'Writes' },
]
export const DEFAULT_KIND = 'write'
const KINDS = new Set(KIND_OPTIONS.map((option) => option.value))

const ENTITY_LABELS = {
  'registry.patient': 'Patient record',
  'accounts.user': 'User account',
  'registry.donorapplication': 'Donor application',
}

/** Filters kept in the page URL. `page` is handled separately by the page. */
export const FILTER_KEYS = ['action', 'kind', 'user', 'patient', 'date_from', 'date_to']

const ID_PATTERN = /^[1-9]\d*$/
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

function isValidDate(value) {
  if (!DATE_PATTERN.test(value)) return false
  const date = new Date(`${value}T00:00:00Z`)
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value
}

/** Field errors for the typed filters (IDs and dates). Empty object when valid. */
export function validateFilters(filters) {
  const errors = {}
  for (const key of ['user', 'patient']) {
    const value = (filters[key] || '').trim()
    if (value && !ID_PATTERN.test(value)) errors[key] = 'Enter a numeric ID.'
  }
  for (const key of ['date_from', 'date_to']) {
    const value = filters[key] || ''
    if (value && !isValidDate(value)) errors[key] = 'Enter a valid date.'
  }
  if (!errors.date_from && !errors.date_to && filters.date_from && filters.date_to
      && filters.date_to < filters.date_from) {
    errors.date_to = 'Must be on or after the start date.'
  }
  return errors
}

/**
 * Reads the filters from URL search params (missing ones become ''). A missing or unknown `kind`
 * becomes the default (writes); `kind=all` in the URL shows reads and writes.
 */
export function readFilters(searchParams) {
  const filters = Object.fromEntries(FILTER_KEYS.map((key) => [key, (searchParams.get(key) || '').trim()]))
  if (!KINDS.has(filters.kind)) filters.kind = DEFAULT_KIND
  return filters
}

/** True when any filter differs from the default view (writes, nothing else set). */
export function hasActiveFilters(filters) {
  return FILTER_KEYS.some((key) => (key === 'kind' ? filters.kind !== DEFAULT_KIND : Boolean(filters[key])))
}

/** URL value for a kind: the default is left out of the URL; 'all' is kept so it survives reloads. */
export function kindParam(kind) {
  return kind === DEFAULT_KIND ? '' : kind
}

/**
 * Filter changes for picking an action. If the action is outside the current type (e.g.
 * "Profile view" while showing writes), the type widens to All so the choice is not hidden.
 */
export function actionChange(action, currentKind) {
  if (!action || currentKind === 'all') return { action }
  const isRead = READ_ACTIONS.has(action)
  const matches = currentKind === 'read' ? isRead : !isRead
  return matches ? { action } : { action, kind: 'all' }
}

/**
 * API query parameters for the current filters: drops empty values, unknown actions/kinds and
 * anything that fails validation, so a hand-edited URL never sends a bad request.
 */
export function toApiParams(filters) {
  const errors = validateFilters(filters)
  const params = {}
  for (const key of FILTER_KEYS) {
    const value = (filters[key] || '').trim()
    if (!value || errors[key]) continue
    if (key === 'action' && !(value in ACTION_LABELS)) continue
    if (key === 'kind' && value !== 'read' && value !== 'write') continue  // 'all' = no type filter
    params[key] = value
  }
  return params
}

export function actionLabel(action) {
  return ACTION_LABELS[action] || action
}

/** Read/write indicator for an entry: { label, tone } for <Badge>. */
export function entryKind(entry) {
  const isRead = entry.is_read ?? READ_ACTIONS.has(entry.action)
  if (isRead) return { label: 'Read', tone: 'info' }
  if (entry.action === 'login' || entry.action === 'logout') return { label: 'Session', tone: 'neutral' }
  return { label: 'Write', tone: 'warning' }
}

/** "Patient record #12", "User account #4", or the raw table name for other entities. */
export function describeRecord(entry) {
  const label = ENTITY_LABELS[entry.entity_type] || entry.entity_type
  return entry.entity_id != null ? `${label} #${entry.entity_id}` : label
}
