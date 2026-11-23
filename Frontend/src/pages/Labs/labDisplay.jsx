import Badge from '../../components/ui/Badge'

export const STATUS_LABELS = {
  ordered: 'Ordered',
  partially_resulted: 'Partially resulted',
  resulted: 'Resulted',
  cancelled: 'Cancelled',
}

export const STATUS_OPTIONS = Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label }))

export const PRIORITY_OPTIONS = [
  { value: 'routine', label: 'Routine' },
  { value: 'urgent', label: 'Urgent' },
]

const STATUS_TONES = { ordered: 'info', partially_resulted: 'warning', resulted: 'success', cancelled: 'neutral' }

export function statusBadge(status) {
  return <Badge tone={STATUS_TONES[status] || 'neutral'}>{STATUS_LABELS[status] || status}</Badge>
}

export function priorityBadge(priority) {
  return priority === 'urgent' ? <Badge tone="danger">Urgent</Badge> : <Badge>Routine</Badge>
}

// The arrow keeps the meaning when colour alone is not enough (colour-blind readers, print).
const FLAGS = {
  normal: { tone: 'success', label: 'Normal' },
  low: { tone: 'warning', label: 'Low ↓' },
  high: { tone: 'warning', label: 'High ↑' },
  critical: { tone: 'danger', label: 'Critical ‼' },
}

export function flagBadge(flag) {
  const info = FLAGS[flag]
  return info ? <Badge tone={info.tone}>{info.label}</Badge> : <span className="muted-text">—</span>
}

export const flagText = (flag) => FLAGS[flag]?.label || ''
