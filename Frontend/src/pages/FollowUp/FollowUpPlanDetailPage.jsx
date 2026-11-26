/* Follow-up Plan Detail – shows plan info, visit list, new visit form, recovery charts. */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import Badge from '../../components/ui/Badge'
import PageHeader from '../../components/ui/PageHeader'
import { Pagination } from '../../components/ui/Feedback'
import { DoctorAvailability } from '../Appointments/appointmentParts'
import { listDoctors } from '../../api/scheduling'
import { fieldErrors } from '../../api/http'
import { useAuth } from '../../auth/authContext'
import { useApi } from '../../hooks/useApi'
import {
  getFollowUpPlan, updateFollowUpPlan,
  listFollowUpVisits, createFollowUpVisit, updateFollowUpVisit,
  getRecoveryStats,
} from '../../api/transplant'
import './FollowUp.css'

const VISIT_PAGE_SIZE = 10
const ROLE_LABELS = { recipient: 'Recipient', donor: 'Donor' }
const VISIT_STATUSES = {
  scheduled: { label: 'Scheduled', tone: 'info' },
  completed: { label: 'Completed', tone: 'success' },
  missed: { label: 'Missed', tone: 'warning' },
  cancelled: { label: 'Cancelled', tone: 'danger' },
}

function visitStatus(status) {
  return VISIT_STATUSES[status] || { label: status || 'Unknown', tone: 'neutral' }
}

export default function FollowUpPlanDetailPage() {
  const { id } = useParams()
  const { can } = useAuth()
  const canManage = can('transplant.manage_followup')
  const [visitPage, setVisitPage] = useState(1)

  /* ── Data loading ───────────────────────────────────────────── */
  const planLoader = useCallback(() => getFollowUpPlan(id), [id])
  const visitsLoader = useCallback(() => listFollowUpVisits(id, { page: visitPage, page_size: VISIT_PAGE_SIZE }), [id, visitPage])
  const statsLoader = useCallback(() => getRecoveryStats(id), [id])

  const { data: plan, loading: planLoading, error: planError, reload: reloadPlan } = useApi(planLoader)
  const { data: visitsRaw, loading: visitsLoading, reload: reloadVisits } = useApi(visitsLoader)
  const { data: stats, reload: reloadStats } = useApi(statsLoader)
  const visits = Array.isArray(visitsRaw) ? visitsRaw : visitsRaw?.results || []
  const visitsCount = visitsRaw?.count ?? visits.length
  const unresolvedVisitCount = plan?.unresolved_visit_count ?? 0
  const refreshTimer = useRef(null)

  // A patient may cancel from their portal while this coordinator screen is open.
  // Refresh once when the coordinator returns to this tab so the visit status is current.
  useEffect(() => {
    function refreshWhenVisible() {
      if (document.visibilityState !== 'visible' || refreshTimer.current !== null) return
      // Browsers emit both `visibilitychange` and `focus` when a tab is reopened.
      // Coalesce them into one refresh instead of repeatedly replacing the page with a loader.
      refreshTimer.current = window.setTimeout(() => {
        reloadPlan()
        reloadVisits()
        reloadStats()
        refreshTimer.current = null
      }, 100)
    }

    window.addEventListener('focus', refreshWhenVisible)
    document.addEventListener('visibilitychange', refreshWhenVisible)
    return () => {
      window.removeEventListener('focus', refreshWhenVisible)
      document.removeEventListener('visibilitychange', refreshWhenVisible)
      if (refreshTimer.current !== null) window.clearTimeout(refreshTimer.current)
    }
  }, [reloadPlan, reloadStats, reloadVisits])

  /* ── New-visit modal state ──────────────────────────────────── */
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ staff: '', start_time: '' })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState(null)
  const doctorsLoader = useCallback(() => listDoctors(), [])
  const { data: doctorsData, error: doctorsError } = useApi(doctorsLoader)
  const hepatologists = (doctorsData || []).filter((doctor) => doctor.job_title === 'hepatologist')

  /* ── Edit-visit inline state ────────────────────────────────── */
  const [editingVisitId, setEditingVisitId] = useState(null)
  const [editForm, setEditForm] = useState({})

  /* ── Complete-plan action ───────────────────────────────────── */
  const [completing, setCompleting] = useState(false)

  if (planLoading && !plan) return <p>Loading plan…</p>
  if (planError) return <p className="error-text">Error: {planError.message}</p>
  if (!plan) return null

  const isRecipient = plan.patient_role === 'recipient'
  const isDonor = plan.patient_role === 'donor'

  /* ── Handlers ───────────────────────────────────────────────── */
  async function handleCreateVisit(e) {
    e.preventDefault()
    setSaving(true)
    setFormError(null)
    try {
      await createFollowUpVisit(id, form)
      setShowModal(false)
      setForm({ staff: '', start_time: '' })
      reloadPlan()
      reloadVisits()
      reloadStats?.()
    } catch (err) {
      setFormError(Object.values(fieldErrors(err)).join(' ') || err.message || 'Could not schedule the follow-up visit.')
    }
    finally { setSaving(false) }
  }

  async function handleCompletePlan() {
    if (!window.confirm('Mark this follow-up plan as completed?')) return
    setCompleting(true)
    try {
      const today = new Date().toISOString().slice(0, 10)
      await updateFollowUpPlan(id, { status: 'completed', end_date: today })
      reloadPlan()
      reloadStats?.()
    } catch (err) {
      alert(Object.values(fieldErrors(err)).join(' ') || err.message || 'Could not complete the follow-up plan.')
    }
    finally { setCompleting(false) }
  }

  function startEditVisit(v) {
    setEditingVisitId(v.id)
    setEditForm({
      immuno_level: v.immuno_level || '',
      rejection_episode: v.rejection_episode || false,
      liver_regrowth_ml: v.liver_regrowth_ml || '',
      complications: v.complications || '',
      notes: v.notes || '',
    })
  }

  async function handleSaveVisit(e) {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = { ...editForm, status: 'completed' }
      // Convert numeric strings
      if (payload.immuno_level === '') delete payload.immuno_level
      else payload.immuno_level = parseFloat(payload.immuno_level)
      if (payload.liver_regrowth_ml === '') delete payload.liver_regrowth_ml
      else payload.liver_regrowth_ml = parseFloat(payload.liver_regrowth_ml)
      await updateFollowUpVisit(editingVisitId, payload)
      setEditingVisitId(null)
      reloadPlan()
      reloadVisits()
      reloadStats?.()
    } catch (err) { alert(err.message) }
    finally { setSaving(false) }
  }

  /* ── Recovery charts helper ─────────────────────────────────── */
  function renderRecoveryCharts() {
    if (!stats || !stats.visits || stats.visits.length === 0) {
      return <p className="chart-empty">No visit data to chart yet.</p>
    }
    const chartVisits = stats.visits.slice(-12) // last 12 visits
    const maxImmuno = Math.max(...chartVisits.map(v => v.immuno_level || 0), 1)
    const maxRegrowth = Math.max(...chartVisits.map(v => v.liver_regrowth_ml || 0), 1)

    return (
      <div className="chart-row">
        {isRecipient && (
          <div className="mini-chart">
            <h4>Immunosuppression Level</h4>
            <div className="bar-chart">
              {chartVisits.map((v, i) => (
                <div
                  key={i}
                  className={`bar${v.rejection_episode ? ' alert' : ''}`}
                  style={{ height: `${((v.immuno_level || 0) / maxImmuno) * 100}%` }}
                  title={`Visit ${i + 1}: ${v.immuno_level ?? '—'}${v.rejection_episode ? ' ⚠ rejection' : ''}`}
                >
                  <span className="bar-label">{v.due_date?.slice(5) || i + 1}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {isRecipient && (
          <div className="mini-chart">
            <h4>Rejection Episodes</h4>
            <div className="bar-chart">
              {chartVisits.map((v, i) => (
                <div
                  key={i}
                  className={`bar${v.rejection_episode ? ' alert' : ''}`}
                  style={{ height: v.rejection_episode ? '100%' : '8%' }}
                  title={`Visit ${i + 1}: ${v.rejection_episode ? 'YES' : 'No'}`}
                >
                  <span className="bar-label">{v.due_date?.slice(5) || i + 1}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {isDonor && (
          <div className="mini-chart">
            <h4>Liver Regrowth (mL)</h4>
            <div className="bar-chart">
              {chartVisits.map((v, i) => (
                <div
                  key={i}
                  className="bar"
                  style={{ height: `${((v.liver_regrowth_ml || 0) / maxRegrowth) * 100}%` }}
                  title={`Visit ${i + 1}: ${v.liver_regrowth_ml ?? '—'} mL`}
                >
                  <span className="bar-label">{v.due_date?.slice(5) || i + 1}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  /* ── Render ──────────────────────────────────────────────────── */
  return (
    <div className="followup-page">
      <PageHeader
        title={`Follow-up Plan #${plan.id}`}
        back={{ to: '/followup', label: 'All plans' }}
        eyebrow={`${ROLE_LABELS[plan.patient_role]} follow-up`}
      />

      {/* Plan info cards */}
      <div className="case-info-grid" style={{ marginBottom: '1.5rem' }}>
        <div className="info-card">
          <label>Patient</label>
          <div className="value">{plan.patient_detail?.full_name || 'Patient details unavailable'}</div>
        </div>
        <div className="info-card">
          <label>Role</label>
          <div className="value">{ROLE_LABELS[plan.patient_role]}</div>
        </div>
        <div className="info-card">
          <label>Transplant Case</label>
          <div className="value">
            <Link to={`/transplant/cases/${plan.case}`}>Case #{plan.case}</Link>
          </div>
        </div>
        <div className="info-card">
          <label>Status</label>
          <Badge tone={plan.status === 'active' ? 'info' : 'success'}>
            {plan.status === 'active' ? 'Active' : 'Completed'}
          </Badge>
        </div>
        <div className="info-card">
          <label>Started</label>
          <div className="value">{plan.start_date || '—'}</div>
        </div>
        <div className="info-card">
          <label>Ended</label>
          <div className="value">{plan.end_date || '—'}</div>
        </div>
      </div>

      {/* Actions */}
      {canManage && plan.status === 'active' && (
        <div className="status-actions" style={{ marginBottom: '1.5rem' }}>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            + Schedule Visit
          </button>
          <span title={unresolvedVisitCount > 0
            ? 'Complete or cancel every follow-up visit before completing this plan.'
            : undefined}
          >
            <button
              className="btn btn-success"
              onClick={handleCompletePlan}
              disabled={completing || unresolvedVisitCount > 0}
            >
              {completing ? 'Completing…' : 'Complete Plan'}
            </button>
          </span>
        </div>
      )}

      {/* Recovery Charts */}
      <div className="section-panel recovery-section">
        <h3>Recovery Trends</h3>
        {renderRecoveryCharts()}
      </div>

      {/* Visits list */}
      <div className="section-panel" style={{ marginTop: '1.25rem' }}>
        <h3>
          Visits
          <span style={{ fontWeight: 400, fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            {' '}({visitsCount} total)
          </span>
        </h3>

        {visitsLoading && <p>Loading visits…</p>}

        <div className="visit-timeline">
          {visits.map((v) => (
            <div key={v.id}>
              {editingVisitId === v.id ? (
                /* ── Inline edit form ── */
                <form className="section-panel" onSubmit={handleSaveVisit} style={{ border: '2px solid var(--primary, #2563eb)' }}>
                  <h3 style={{ fontSize: '0.875rem' }}>Edit visit – {v.due_date}</h3>
                  <div className="form-grid">
                    {isRecipient && (
                      <>
                        <div className="form-group">
                          <label>Immuno level</label>
                          <input
                            type="number" step="0.01"
                            value={editForm.immuno_level}
                            onChange={(e) => setEditForm({ ...editForm, immuno_level: e.target.value })}
                          />
                        </div>
                        <div className="form-group">
                          <label>Rejection episode?</label>
                          <select
                            value={editForm.rejection_episode ? 'yes' : 'no'}
                            onChange={(e) => setEditForm({ ...editForm, rejection_episode: e.target.value === 'yes' })}
                          >
                            <option value="no">No</option>
                            <option value="yes">Yes</option>
                          </select>
                        </div>
                      </>
                    )}
                    {isDonor && (
                      <div className="form-group">
                        <label>Liver regrowth (mL)</label>
                        <input
                          type="number" step="0.1"
                          value={editForm.liver_regrowth_ml}
                          onChange={(e) => setEditForm({ ...editForm, liver_regrowth_ml: e.target.value })}
                        />
                      </div>
                    )}
                    <div className="form-group">
                      <label>Complications</label>
                      <textarea
                        rows={2}
                        value={editForm.complications}
                        onChange={(e) => setEditForm({ ...editForm, complications: e.target.value })}
                      />
                    </div>
                    <div className="form-group">
                      <label>Notes</label>
                      <textarea
                        rows={2}
                        value={editForm.notes}
                        onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                      />
                    </div>
                  </div>
                  <div className="form-actions">
                    <button type="submit" className="btn btn-primary" disabled={saving}>
                      {saving ? 'Saving…' : 'Save'}
                    </button>
                    <button type="button" className="btn" onClick={() => setEditingVisitId(null)}>Cancel</button>
                  </div>
                </form>
              ) : (
                /* ── Visit card ── */
                <div className="visit-card">
                  <div className="visit-card__info">
                    <span className="visit-card__date">{v.due_date}</span>
                    <span className="visit-card__detail">
                      {isRecipient && v.immuno_level != null && `Immuno: ${v.immuno_level}`}
                      {isRecipient && v.rejection_episode && ' ⚠ Rejection'}
                      {isDonor && v.liver_regrowth_ml != null && `Regrowth: ${v.liver_regrowth_ml} mL`}
                      {v.complications && ` | Complications: ${v.complications}`}
                    </span>
                    {v.notes && (
                      <span className="visit-card__detail" style={{ fontStyle: 'italic' }}>
                        {v.notes}
                      </span>
                    )}
                  </div>
                  <div className="visit-card__actions">
                    <Badge tone={visitStatus(v.status).tone}>
                      {visitStatus(v.status).label}
                    </Badge>
                    {canManage && plan.status === 'active' && v.status === 'scheduled' && (
                      <button className="btn" onClick={() => startEditVisit(v)}>Edit</button>
                    )}
                    {v.appointment && (
                      <span className="visit-card__detail">Appt #{v.appointment}</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {!visitsLoading && visits.length === 0 && (
            <p style={{ color: 'var(--text-secondary)', textAlign: 'center' }}>No visits recorded yet.</p>
          )}
        </div>

        <Pagination
          page={visitPage}
          pageSize={VISIT_PAGE_SIZE}
          count={visitsCount}
          onPageChange={setVisitPage}
        />
      </div>

      {/* ── New visit modal ───────────────────────────────────── */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h2>Schedule New Visit</h2>
            {formError && <p className="error-text">{formError}</p>}
            <form onSubmit={handleCreateVisit}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Hepatologist *</label>
                  <select
                    required
                    value={form.staff}
                    onChange={(e) => setForm({ staff: e.target.value, start_time: '' })}
                  >
                    <option value="">— Select hepatologist —</option>
                    {hepatologists.map((doctor) => (
                      <option key={doctor.staff_id} value={doctor.staff_id}>{doctor.name}</option>
                    ))}
                  </select>
                  {doctorsError && <p className="error-text">Could not load hepatologists.</p>}
                  {!doctorsError && doctorsData && hepatologists.length === 0 && (
                    <p className="error-text">No active hepatologists are available.</p>
                  )}
                </div>
              </div>
              <DoctorAvailability
                staff={form.staff}
                value={form.start_time}
                onSelect={(_, start_time) => setForm({ ...form, start_time })}
              />
              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={saving || !form.staff || !form.start_time}>
                  {saving ? 'Scheduling…' : 'Schedule Visit'}
                </button>
                <button type="button" className="btn" onClick={() => setShowModal(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
