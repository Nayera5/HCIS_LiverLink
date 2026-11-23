/* Transplant Cases Dashboard – list all cases with filters and search. */
import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../auth/authContext'
import Badge from '../../components/ui/Badge'
import PageHeader from '../../components/ui/PageHeader'
import { useApi } from '../../hooks/useApi'
import { listCases } from '../../api/transplant'
import './Transplant.css'

const STATUS_COLORS = {
  referred: 'info', under_evaluation: 'warning', committee_review: 'warning',
  approved: 'success', rejected: 'danger', surgery_scheduled: 'info',
  transplanted: 'success', follow_up: 'info', closed: 'neutral',
}

const STATUS_LABELS = {
  referred: 'Referred', under_evaluation: 'Under evaluation', committee_review: 'Committee review',
  approved: 'Approved', rejected: 'Rejected', surgery_scheduled: 'Surgery scheduled',
  transplanted: 'Transplanted', follow_up: 'Follow-up', closed: 'Closed',
}

export default function TransplantCasesPage() {
  const { can } = useAuth()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const loader = useCallback(
    () => listCases({ search, status: statusFilter }),
    [search, statusFilter],
  )
  const { data, loading, error } = useApi(loader)
  const cases = Array.isArray(data) ? data : data?.results || []

  return (
    <div className="transplant-page">
      <PageHeader
        title="Transplant Cases"
        actions={
          can('transplant.refer') && (
            <Link to="/transplant/new" className="btn btn-primary">+ New Referral</Link>
          )
        }
      />

      <div className="filters-row">
        <input
          type="text" placeholder="Search by patient name or MRN…"
          value={search} onChange={(e) => setSearch(e.target.value)}
          className="input"
        />
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input">
          <option value="">All statuses</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>

      {error && <p className="error-text">{error.message}</p>}
      {loading && <p>Loading…</p>}

      <table className="data-table">
        <thead>
          <tr>
            <th>Case #</th>
            <th>Recipient</th>
            <th>MRN</th>
            <th>Status</th>
            <th>Donors</th>
            <th>Checklist</th>
            <th>Referral Date</th>
            <th>Coordinator</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.id}>
              <td><Link to={`/transplant/cases/${c.id}`}>#{c.id}</Link></td>
              <td>{c.recipient_name}</td>
              <td>{c.recipient_mrn}</td>
              <td><Badge variant={STATUS_COLORS[c.status]}>{STATUS_LABELS[c.status]}</Badge></td>
              <td>{c.donor_count}</td>
              <td>
                {c.checklist_progress?.total > 0
                  ? `${c.checklist_progress.done}/${c.checklist_progress.total} (${c.checklist_progress.percent}%)`
                  : '—'}
              </td>
              <td>{c.referral_date}</td>
              <td>{c.coordinator_name || '—'}</td>
            </tr>
          ))}
          {!loading && cases.length === 0 && (
            <tr><td colSpan="8" className="empty-row">No transplant cases found.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
