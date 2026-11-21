import Badge from '../../components/ui/Badge'
import { JOB_TITLE_LABELS, ROLE_LABELS } from '../../auth/roles'

/** Status badge for an account row. */
export function accountBadge(account) {
  if (!account.is_active) return <Badge tone="danger">Deactivated</Badge>
  if (account.role !== 'patient' && !account.job_title && !account.is_superuser) {
    return <Badge tone="warning">No job title</Badge>
  }
  return <Badge tone="success">Active</Badge>
}

/** "Hepatologist", "System admin" (superuser without profile), or the role label. */
export function accountTitle(account) {
  if (account.job_title) return JOB_TITLE_LABELS[account.job_title] || account.job_title
  if (account.is_superuser) return 'System admin'
  return ROLE_LABELS[account.role] || account.role
}
