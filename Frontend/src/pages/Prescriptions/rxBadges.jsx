import Badge from '../../components/ui/Badge'
import { formatDate } from '../../utils/format'

const RX_STATUS = {
  active: { tone: 'success', label: 'Active' },
  stopped: { tone: 'danger', label: 'Stopped' },
  completed: { tone: 'neutral', label: 'Completed' },
}

const PLAN_STATUS = {
  active: { tone: 'success', label: 'Active' },
  completed: { tone: 'neutral', label: 'Completed' },
  cancelled: { tone: 'danger', label: 'Cancelled' },
}

export function rxStatusBadge(rx) {
  // An active prescription past its end date is shown as finished.
  if (rx.status === 'active' && rx.is_current === false) return <Badge tone="neutral">Course ended</Badge>
  const s = RX_STATUS[rx.status] || { tone: 'neutral', label: rx.status }
  return <Badge tone={s.tone}>{s.label}</Badge>
}

export function planStatusBadge(status) {
  const s = PLAN_STATUS[status] || { tone: 'neutral', label: status }
  return <Badge tone={s.tone}>{s.label}</Badge>
}

export function periodText(rx) {
  return rx.end_date ? `${formatDate(rx.start_date)} – ${formatDate(rx.end_date)}` : `From ${formatDate(rx.start_date)} (ongoing)`
}
