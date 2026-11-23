/* Transplant Case Detail – the main case hub with tabs for donors, checklist, decisions, surgery. */
import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../../auth/authContext'
import Badge from '../../components/ui/Badge'
import PageHeader from '../../components/ui/PageHeader'
import { useApi } from '../../hooks/useApi'
import {
  getCase, updateCaseStatus, listCaseDonors, addCaseDonor, updateDonorStatus, checkABO,
  listChecklist, createChecklistItem, updateChecklistStatus, deleteChecklistItem,
  listDecisions, createDecision, listSurgeries, createSurgery, completeSurgery,
} from '../../api/transplant'
import { listPatients } from '../../api/patients'
import { fieldErrors } from '../../api/http'
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

export default function TransplantCaseDetailPage() {
  const { id } = useParams()
  const { can } = useAuth()
  const [tab, setTab] = useState('overview')
  const [actionError, setActionError] = useState('')

  const caseLoader = useCallback(() => getCase(id), [id])
  const { data: caseData, loading, error, reload } = useApi(caseLoader)

  const donorsLoader = useCallback(() => listCaseDonors(id), [id])
  const { data: donors, reload: reloadDonors } = useApi(donorsLoader)

  const checklistLoader = useCallback(() => listChecklist(id), [id])
  const { data: checklist, reload: reloadChecklist } = useApi(checklistLoader)

  const decisionsLoader = useCallback(() => listDecisions(id), [id])
  const { data: decisions, reload: reloadDecisions } = useApi(decisionsLoader)

  const surgeriesLoader = useCallback(() => listSurgeries(id), [id])
  const { data: surgeries, reload: reloadSurgeries } = useApi(surgeriesLoader)

  if (loading) return <p>Loading…</p>
  if (error) return <p className="error-text">{error.message}</p>
  if (!caseData) return null

  const c = caseData
  const donorList = Array.isArray(donors) ? donors : donors?.results || []
  const checklistItems = Array.isArray(checklist) ? checklist : checklist?.results || []
  const decisionList = Array.isArray(decisions) ? decisions : decisions?.results || []
  const surgeryList = Array.isArray(surgeries) ? surgeries : surgeries?.results || []

  const handleStatusChange = async (newStatus) => {
    setActionError('')
    try {
      await updateCaseStatus(id, newStatus)
      reload()
    } catch (err) {
      setActionError(err.data?.status || err.message)
    }
  }

  return (
    <div className="transplant-page case-detail">
      <PageHeader title={`Transplant Case #${c.id}`}>
        <Link to="/transplant" className="btn">← Back to Cases</Link>
      </PageHeader>

      {/* Case header info */}
      <div className="case-info-grid">
        <div className="info-card">
          <label>Recipient</label>
          <div className="value">{c.recipient.full_name}</div>
          <small>{c.recipient.mrn} · {c.recipient.blood_group || 'Unknown'}</small>
        </div>
        <div className="info-card">
          <label>Status</label>
          <Badge variant={STATUS_COLORS[c.status]}>{STATUS_LABELS[c.status]}</Badge>
        </div>
        <div className="info-card">
          <label>Referred By</label>
          <div className="value">{c.referred_by_detail?.name || '—'}</div>
        </div>
        <div className="info-card">
          <label>Coordinator</label>
          <div className="value">{c.coordinator_detail?.name || 'Not assigned'}</div>
        </div>
        <div className="info-card">
          <label>Referral Date</label>
          <div className="value">{c.referral_date}</div>
        </div>
        <div className="info-card">
          <label>Checklist</label>
          <div className="value">{c.checklist_progress.done}/{c.checklist_progress.total} items</div>
          <div className="checklist-progress-bar">
            <div className="checklist-progress-fill" style={{ width: `${c.checklist_progress.percent}%` }} />
          </div>
        </div>
      </div>

      {/* Status transitions */}
      {can('transplant.manage') && c.available_transitions?.length > 0 && (
        <div className="section-panel">
          <h3>Actions</h3>
          <div className="status-actions">
            {c.available_transitions.map((s) => (
              <button key={s} className={`btn ${s === 'approved' ? 'btn-success' : s === 'rejected' ? 'btn-danger' : 'btn-primary'}`}
                onClick={() => handleStatusChange(s)}>
                Move to: {STATUS_LABELS[s] || s}
              </button>
            ))}
          </div>
          {actionError && <p className="error-text" style={{ marginTop: 8 }}>{actionError}</p>}
        </div>
      )}

      {/* Tabs */}
      <div className="tabs">
        {['overview', 'donors', 'checklist', 'decisions', 'surgery'].map((t) => (
          <button key={t} className={`tab-btn ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === 'overview' && <OverviewTab c={c} donorList={donorList} />}
      {tab === 'donors' && <DonorsTab caseId={id} donors={donorList} reload={reloadDonors} can={can} />}
      {tab === 'checklist' && <ChecklistTab caseId={id} items={checklistItems} reload={reloadChecklist} can={can} />}
      {tab === 'decisions' && <DecisionsTab caseId={id} decisions={decisionList} reload={reloadDecisions} caseStatus={c.status} can={can} reloadCase={reload} />}
      {tab === 'surgery' && <SurgeryTab caseId={id} surgeries={surgeryList} donors={donorList} reload={reloadSurgeries} caseStatus={c.status} can={can} reloadCase={reload} />}
    </div>
  )
}

/* ── Overview Tab ─────────────────────────────────────────────────────── */
function OverviewTab({ c, donorList }) {
  return (
    <div>
      <div className="section-panel">
        <h3>Candidate Donors ({donorList.length})</h3>
        {donorList.length === 0 ? <p>No donors added yet.</p> : (
          <table className="data-table">
            <thead><tr><th>Donor</th><th>MRN</th><th>Blood Group</th><th>ABO</th><th>Status</th></tr></thead>
            <tbody>
              {donorList.map((d) => (
                <tr key={d.id}>
                  <td>{d.donor_detail?.full_name}</td>
                  <td>{d.donor_detail?.mrn}</td>
                  <td>{d.donor_detail?.blood_group || '—'}</td>
                  <td>
                    <span className={`abo-result ${d.abo_compatible === true ? 'compatible' : d.abo_compatible === false ? 'incompatible' : 'unknown'}`}>
                      {d.abo_compatible === true ? '✓ Compatible' : d.abo_compatible === false ? '✗ Incompatible' : '? Unknown'}
                    </span>
                  </td>
                  <td><Badge>{d.status}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

/* ── Donors Tab ──────────────────────────────────────────────────────── */
function DonorsTab({ caseId, donors, reload, can }) {
  const [adding, setAdding] = useState(false)
  const [donorSearch, setDonorSearch] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [err, setErr] = useState('')

  const search = async (q) => {
    setDonorSearch(q)
    if (q.length < 2) { setSearchResults([]); return }
    try {
      const res = await listPatients({ search: q, category: 'donor', page_size: 10 })
      setSearchResults(res.results || [])
    } catch { /* ignore */ }
  }

  const addDonor = async (patientId) => {
    setErr('')
    try {
      await addCaseDonor(caseId, { donor: patientId, case: caseId })
      setAdding(false); setDonorSearch(''); setSearchResults([])
      reload()
    } catch (e) { setErr(Object.values(fieldErrors(e)).join(' ') || e.message) }
  }

  const handleStatusChange = async (donorId, newStatus) => {
    try { await updateDonorStatus(donorId, newStatus); reload() } catch { /* ignore */ }
  }

  const handleAboCheck = async (donorId) => {
    try { await checkABO(donorId); reload() } catch { /* ignore */ }
  }

  return (
    <div className="section-panel">
      <h3>
        Candidate Donors
        {can('transplant.manage') && <button className="btn btn-primary" onClick={() => setAdding(!adding)}>+ Add Donor</button>}
      </h3>
      {adding && (
        <div style={{ marginBottom: '1rem', padding: '1rem', border: '1px solid #e5e7eb', borderRadius: 8 }}>
          <input type="text" placeholder="Search donors by name or MRN…" value={donorSearch} onChange={(e) => search(e.target.value)} className="input" style={{ width: '100%', marginBottom: 8 }} />
          {searchResults.map((p) => (
            <div key={p.id} style={{ padding: '0.4rem 0.5rem', cursor: 'pointer', borderBottom: '1px solid #f3f4f6' }} onClick={() => addDonor(p.id)}>
              {p.mrn} · {p.full_name}
            </div>
          ))}
          {err && <p className="error-text">{err}</p>}
        </div>
      )}
      <table className="data-table">
        <thead><tr><th>Donor</th><th>MRN</th><th>Blood Group</th><th>ABO</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>
          {donors.map((d) => (
            <tr key={d.id}>
              <td>{d.donor_detail?.full_name}</td>
              <td>{d.donor_detail?.mrn}</td>
              <td>{d.donor_detail?.blood_group || '—'}</td>
              <td>
                <span className={`abo-result ${d.abo_compatible === true ? 'compatible' : d.abo_compatible === false ? 'incompatible' : 'unknown'}`}>
                  {d.abo_compatible === true ? '✓ Compatible' : d.abo_compatible === false ? '✗ Incompatible' : '? Unknown'}
                </span>
              </td>
              <td><Badge>{d.status}</Badge></td>
              <td>
                <button className="btn" onClick={() => handleAboCheck(d.id)}>Check ABO</button>
                {can('transplant.manage') && d.status !== 'approved' && d.status !== 'withdrawn' && (
                  <>
                    <button className="btn btn-success" onClick={() => handleStatusChange(d.id, 'approved')} style={{ marginLeft: 4 }}>Approve</button>
                    <button className="btn" onClick={() => handleStatusChange(d.id, 'not_suitable')} style={{ marginLeft: 4 }}>Not Suitable</button>
                  </>
                )}
              </td>
            </tr>
          ))}
          {donors.length === 0 && <tr><td colSpan="6" className="empty-row">No donors added yet.</td></tr>}
        </tbody>
      </table>
    </div>
  )
}

/* ── Checklist Tab ───────────────────────────────────────────────────── */
function ChecklistTab({ caseId, items, reload, can }) {
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ item_name: '', item_type: 'lab_test', patient: '', is_required: true })

  const handleAdd = async () => {
    if (!form.item_name || !form.patient) return
    try {
      await createChecklistItem(caseId, { ...form, case: caseId })
      setAdding(false); setForm({ item_name: '', item_type: 'lab_test', patient: '', is_required: true })
      reload()
    } catch { /* ignore */ }
  }

  const toggleStatus = async (item, newStatus) => {
    try { await updateChecklistStatus(item.id, newStatus); reload() } catch { /* ignore */ }
  }

  const handleDelete = async (id) => {
    try { await deleteChecklistItem(id); reload() } catch { /* ignore */ }
  }

  const done = items.filter((i) => i.status !== 'pending').length
  const total = items.length

  return (
    <div className="section-panel">
      <h3>
        Evaluation Checklist ({done}/{total})
        {can('transplant.manage') && <button className="btn btn-primary" onClick={() => setAdding(!adding)}>+ Add Item</button>}
      </h3>
      {total > 0 && (
        <div className="checklist-progress-bar" style={{ marginBottom: '1rem' }}>
          <div className="checklist-progress-fill" style={{ width: `${total > 0 ? Math.round(done / total * 100) : 0}%` }} />
        </div>
      )}
      {adding && (
        <div style={{ marginBottom: '1rem', padding: '1rem', border: '1px solid #e5e7eb', borderRadius: 8 }}>
          <div className="form-grid">
            <div className="form-group">
              <label>Item Name</label>
              <input value={form.item_name} onChange={(e) => setForm({ ...form, item_name: e.target.value })} className="input" />
            </div>
            <div className="form-group">
              <label>Type</label>
              <select value={form.item_type} onChange={(e) => setForm({ ...form, item_type: e.target.value })} className="input">
                <option value="lab_test">Lab Test</option>
                <option value="imaging">Imaging</option>
                <option value="consultation">Consultation</option>
                <option value="document">Document</option>
              </select>
            </div>
            <div className="form-group">
              <label>Patient ID (recipient or donor)</label>
              <input type="number" value={form.patient} onChange={(e) => setForm({ ...form, patient: e.target.value })} className="input" />
            </div>
            <div className="form-group">
              <label><input type="checkbox" checked={form.is_required} onChange={(e) => setForm({ ...form, is_required: e.target.checked })} /> Required</label>
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleAdd} style={{ marginTop: 8 }}>Add Item</button>
        </div>
      )}
      <table className="data-table">
        <thead><tr><th>Item</th><th>Type</th><th>Patient</th><th>Required</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.item_name}</td>
              <td>{item.item_type}</td>
              <td>{item.patient_name}</td>
              <td>{item.is_required ? 'Yes' : 'No'}</td>
              <td><Badge variant={item.status === 'done' ? 'success' : item.status === 'waived' ? 'neutral' : 'warning'}>{item.status}</Badge></td>
              <td>
                {can('transplant.manage') && (
                  <>
                    {item.status === 'pending' && <button className="btn btn-success" onClick={() => toggleStatus(item, 'done')}>Done</button>}
                    {item.status === 'pending' && <button className="btn" onClick={() => toggleStatus(item, 'waived')} style={{ marginLeft: 4 }}>Waive</button>}
                    {item.status !== 'pending' && <button className="btn" onClick={() => toggleStatus(item, 'pending')} style={{ marginLeft: 4 }}>Reset</button>}
                    <button className="btn btn-danger" onClick={() => handleDelete(item.id)} style={{ marginLeft: 4 }}>×</button>
                  </>
                )}
              </td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan="6" className="empty-row">No checklist items.</td></tr>}
        </tbody>
      </table>
    </div>
  )
}

/* ── Decisions Tab ───────────────────────────────────────────────────── */
function DecisionsTab({ caseId, decisions, reload, caseStatus, can, reloadCase }) {
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ meeting_date: '', decision: '', reasons: '', extra_tests: '' })

  const submit = async () => {
    try {
      await createDecision(caseId, form)
      setAdding(false)
      setForm({ meeting_date: '', decision: '', reasons: '', extra_tests: '' })
      reload(); reloadCase()
    } catch { /* ignore */ }
  }

  return (
    <div className="section-panel">
      <h3>
        Committee Decisions
        {can('transplant.committee_decide') && caseStatus === 'committee_review' && (
          <button className="btn btn-primary" onClick={() => setAdding(!adding)}>+ Record Decision</button>
        )}
      </h3>
      {adding && (
        <div style={{ marginBottom: '1rem', padding: '1rem', border: '1px solid #e5e7eb', borderRadius: 8 }}>
          <div className="form-grid">
            <div className="form-group">
              <label>Meeting Date</label>
              <input type="date" value={form.meeting_date} onChange={(e) => setForm({ ...form, meeting_date: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Decision</label>
              <select value={form.decision} onChange={(e) => setForm({ ...form, decision: e.target.value })}>
                <option value="">— Select —</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="more_tests_needed">More Tests Needed</option>
              </select>
            </div>
            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label>Reasons</label>
              <textarea rows={3} value={form.reasons} onChange={(e) => setForm({ ...form, reasons: e.target.value })} />
            </div>
            {form.decision === 'more_tests_needed' && (
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Extra Tests Requested</label>
                <textarea rows={2} value={form.extra_tests} onChange={(e) => setForm({ ...form, extra_tests: e.target.value })} />
              </div>
            )}
          </div>
          <button className="btn btn-primary" onClick={submit} style={{ marginTop: 8 }}>Save Decision</button>
        </div>
      )}
      {decisions.map((d) => (
        <div key={d.id} style={{ padding: '1rem', borderBottom: '1px solid #e5e7eb' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <strong>Decision: <Badge variant={d.decision === 'approved' ? 'success' : d.decision === 'rejected' ? 'danger' : 'warning'}>{d.decision || 'Pending'}</Badge></strong>
            <small>{d.meeting_date} · by {d.recorded_by_detail?.name}</small>
          </div>
          <p style={{ margin: '0.5rem 0' }}>{d.reasons}</p>
          {d.extra_tests && <p><strong>Extra tests:</strong> {d.extra_tests}</p>}
          {d.members?.length > 0 && (
            <small>Members: {d.members.map((m) => m.staff_detail?.name || m.staff).join(', ')}</small>
          )}
        </div>
      ))}
      {decisions.length === 0 && <p>No committee decisions recorded yet.</p>}
    </div>
  )
}

/* ── Surgery Tab ─────────────────────────────────────────────────────── */
function SurgeryTab({ caseId, surgeries, donors, reload, caseStatus, can, reloadCase }) {
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ case_donor: '', lead_surgeon: '', scheduled_at: '', operating_room: '', graft_type: '' })

  const approvedDonors = donors.filter((d) => d.status === 'approved')

  const scheduleSurgery = async () => {
    try {
      await createSurgery(caseId, form)
      setAdding(false); reload(); reloadCase()
    } catch { /* ignore */ }
  }

  const handleComplete = async (surgeryId) => {
    try { await completeSurgery(surgeryId); reload(); reloadCase() } catch { /* ignore */ }
  }

  return (
    <div className="section-panel">
      <h3>
        Surgery
        {can('transplant.record_surgery') && caseStatus === 'approved' && approvedDonors.length > 0 && (
          <button className="btn btn-primary" onClick={() => setAdding(!adding)}>+ Schedule Surgery</button>
        )}
      </h3>
      {adding && (
        <div style={{ marginBottom: '1rem', padding: '1rem', border: '1px solid #e5e7eb', borderRadius: 8 }}>
          <div className="form-grid">
            <div className="form-group">
              <label>Approved Donor</label>
              <select value={form.case_donor} onChange={(e) => setForm({ ...form, case_donor: e.target.value })}>
                <option value="">— Select —</option>
                {approvedDonors.map((d) => <option key={d.id} value={d.id}>{d.donor_detail?.full_name}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Scheduled At</label>
              <input type="datetime-local" value={form.scheduled_at} onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Operating Room</label>
              <input value={form.operating_room} onChange={(e) => setForm({ ...form, operating_room: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Graft Type</label>
              <select value={form.graft_type} onChange={(e) => setForm({ ...form, graft_type: e.target.value })}>
                <option value="">— Select —</option>
                <option value="right_lobe">Right Lobe</option>
                <option value="left_lobe">Left Lobe</option>
                <option value="left_lateral_segment">Left Lateral Segment</option>
              </select>
            </div>
            <div className="form-group">
              <label>Lead Surgeon (Staff ID)</label>
              <input type="number" value={form.lead_surgeon} onChange={(e) => setForm({ ...form, lead_surgeon: e.target.value })} />
            </div>
          </div>
          <button className="btn btn-primary" onClick={scheduleSurgery} style={{ marginTop: 8 }}>Schedule Surgery</button>
        </div>
      )}
      {surgeries.map((s) => (
        <div key={s.id} style={{ padding: '1rem', borderBottom: '1px solid #e5e7eb' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <strong>Surgery #{s.id} – <Badge variant={s.status === 'completed' ? 'success' : s.status === 'cancelled' ? 'danger' : 'info'}>{s.status}</Badge></strong>
            <small>{new Date(s.scheduled_at).toLocaleString()}</small>
          </div>
          <p>Donor: {s.case_donor_detail?.donor_detail?.full_name} · Surgeon: {s.lead_surgeon_detail?.name}</p>
          {s.operating_room && <p>OR: {s.operating_room}</p>}
          {s.graft_type && <p>Graft: {s.graft_type}</p>}
          {s.graft_weight_g && <p>Weight: {s.graft_weight_g}g</p>}
          {s.duration_min && <p>Duration: {s.duration_min} min</p>}
          {s.operative_notes && <p>Notes: {s.operative_notes}</p>}
          {s.complications && <p>Complications: {s.complications}</p>}
          {can('transplant.record_surgery') && s.status === 'scheduled' && (
            <button className="btn btn-success" onClick={() => handleComplete(s.id)} style={{ marginTop: 8 }}>Mark Completed</button>
          )}
          {can('transplant.record_surgery') && s.status === 'in_progress' && (
            <button className="btn btn-success" onClick={() => handleComplete(s.id)} style={{ marginTop: 8 }}>Mark Completed</button>
          )}
        </div>
      ))}
      {surgeries.length === 0 && <p>No surgery records yet.</p>}
    </div>
  )
}
