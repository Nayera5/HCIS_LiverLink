/* Follow-up Dashboard – lists all follow-up plans with filters. */
import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import Badge from '../../components/ui/Badge'
import PageHeader from '../../components/ui/PageHeader'
import { Pagination } from '../../components/ui/Feedback'
import { useApi } from '../../hooks/useApi'
import { listFollowUpPlans } from '../../api/transplant'
import './FollowUp.css'

const PAGE_SIZE = 10
const ROLE_LABELS = { recipient: 'Recipient', donor: 'Donor' }
const STATUS_TONES = { active: 'info', completed: 'success' }

export default function FollowUpDashboard() {
  const [roleFilter, setRoleFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)

  const loader = useCallback(
    () => listFollowUpPlans({ patient_role: roleFilter, status: statusFilter, page, page_size: PAGE_SIZE }),
    [roleFilter, statusFilter, page],
  )
  const { data, loading, error } = useApi(loader)
  const plans = Array.isArray(data) ? data : data?.results || []
  const totalCount = data?.count ?? plans.length

  return (
    <div className="followup-page">
      <PageHeader title="Post-Transplant Follow-up" />

      <div className="filters-row">
        <select
          value={roleFilter}
          onChange={(e) => { setRoleFilter(e.target.value); setPage(1) }}
          className="input"
        >
          <option value="">All roles</option>
          <option value="recipient">Recipient</option>
          <option value="donor">Donor</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
          className="input"
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      {error && <p className="error-text">{error.message}</p>}
      {loading && <p>Loading…</p>}

      {!loading && plans.length === 0 && (
        <p className="error-text" style={{ color: 'var(--text-secondary, #6b7280)' }}>
          No follow-up plans found.
        </p>
      )}

      <div className="plan-cards">
        {plans.map((plan) => (
          <Link key={plan.id} to={`/followup/plans/${plan.id}`} className="plan-card">
            <div className="plan-card__header">
              <h3>Case #{plan.case}</h3>
              <Badge tone={STATUS_TONES[plan.status] || 'neutral'}>
                {plan.status === 'active' ? 'Active' : 'Completed'}
              </Badge>
            </div>
            <div className="plan-card__meta">
              <span><strong>Patient:</strong> {plan.patient_name || `Patient #${plan.patient}`}</span>
              <span><strong>Role:</strong> {ROLE_LABELS[plan.patient_role] || plan.patient_role}</span>
              <span><strong>Started:</strong> {plan.start_date || '—'}</span>
              {plan.end_date && <span><strong>Ended:</strong> {plan.end_date}</span>}
            </div>
            <div className="plan-card__stats">
              <div>
                <span className="stat-label">Visits </span>
                <span className="stat-value">{plan.visit_count ?? '—'}</span>
              </div>
              <div>
                <span className="stat-label">Next due </span>
                <span className="stat-value">{plan.next_due_date || '—'}</span>
              </div>
            </div>
          </Link>
        ))}
      </div>

      <Pagination
        page={page}
        pageSize={PAGE_SIZE}
        count={totalCount}
        onPageChange={setPage}
      />
    </div>
  )
}
