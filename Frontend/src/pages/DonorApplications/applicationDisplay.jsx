import Badge from '../../components/ui/Badge'
import { STATUS_TONES, statusLabel } from './donorApplicationRules'

export function statusBadge(status) {
  return <Badge tone={STATUS_TONES[status] || 'neutral'}>{statusLabel(status)}</Badge>
}
