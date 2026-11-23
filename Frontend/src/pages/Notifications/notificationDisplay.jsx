import Badge from '../../components/ui/Badge'

export const TYPE_LABELS = {
  appointment_reminder: 'Appointment reminder',
  result_ready: 'Result ready',
  case_update: 'Case update',
  pending_task: 'Pending task',
  follow_up_reminder: 'Follow-up reminder',
}

const TYPE_TONES = {
  appointment_reminder: 'info',
  result_ready: 'success',
  case_update: 'teal',
  pending_task: 'warning',
  follow_up_reminder: 'info',
}

export function typeBadge(type) {
  return <Badge tone={TYPE_TONES[type] || 'neutral'}>{TYPE_LABELS[type] || type}</Badge>
}
