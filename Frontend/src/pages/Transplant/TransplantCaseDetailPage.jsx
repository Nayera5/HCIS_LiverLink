/* Transplant Case Detail – the main case hub with tabs for donors, checklist, decisions, surgery. */
import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../../auth/authContext'
import Badge from '../../components/ui/Badge'
import PageHeader from '../../components/ui/PageHeader'
import { useApi } from '../../hooks/useApi'
import {
  getCase, updateCase, updateCaseStatus, listCaseDonors, addCaseDonor, updateDonorStatus, checkABO,
  listChecklist, createChecklistItem, updateChecklistStatus, deleteChecklistItem,
  listDecisions, createDecision, listSurgeries, createSurgery, completeSurgery,
  listTransplantStaff, addTeamMember, removeTeamMember,
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
      <PageHeader
        title={`Transplant Case #${c.id}`}
        actions={<Link to="/transplant" className="btn">← Back to Cases</Link>}
      />

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

      {can('transplant.manage') && (
        <CoordinatorAssignment
          caseId={id}
          currentCoordinator={c.coordinator_detail}
          onSaved={reload}
        />
      )}

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

      {tab === 'overview' && <OverviewTab donorList={donorList} />}
      {tab === 'donors' && <DonorsTab caseId={id} caseStatus={c.status} donors={donorList} reload={reloadDonors} can={can} />}
      {tab === 'checklist' && <ChecklistTab caseId={id} recipient={c.recipient} donors={donorList} items={checklistItems} reload={reloadChecklist} can={can} />}
      {tab === 'decisions' && <DecisionsTab caseId={id} decisions={decisionList} reload={reloadDecisions} caseStatus={c.status} can={can} reloadCase={reload} />}
      {tab === 'surgery' && <SurgeryTab caseId={id} surgeries={surgeryList} donors={donorList} reload={reloadSurgeries} caseStatus={c.status} can={can} reloadCase={reload} />}
    </div>
  )
}

/* ── Overview Tab ─────────────────────────────────────────────────────── */
function CoordinatorAssignment({ caseId, currentCoordinator, onSaved }) {
  const [coordinators, setCoordinators] = useState([])
  const [draftId, setDraftId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const selectedId = draftId ?? (currentCoordinator?.id ? String(currentCoordinator.id) : '')

  useEffect(() => {
    let active = true
    listTransplantStaff({ job_title: 'transplant_coordinator' }).then(
      (results) => { if (active) { setCoordinators(results); setLoading(false) } },
      (err) => { if (active) { setError(err.message || 'Could not load coordinators.'); setLoading(false) } },
    )
    return () => { active = false }
  }, [])

  const save = async () => {
    setSaving(true)
    setError('')
    try {
      await updateCase(caseId, { coordinator: selectedId ? Number(selectedId) : null })
      setDraftId(null)
      onSaved()
    } catch (err) {
      setError(err.message || 'Could not update the case coordinator.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="section-panel">
      <h3>Case Coordinator</h3>
      <div className="form-grid">
        <div className="form-group">
          <label htmlFor="case-coordinator-picker">Assign coordinator</label>
          <select
            id="case-coordinator-picker"
            value={selectedId}
            onChange={(e) => setDraftId(e.target.value)}
            disabled={loading || Boolean(error)}
          >
            <option value="">Unassigned</option>
            {coordinators.map((member) => (
              <option key={member.id} value={member.id}>{member.name}</option>
            ))}
          </select>
        </div>
      </div>
      {error && <p className="error-text">{error}</p>}
      <button className="btn btn-primary" onClick={save} disabled={loading || saving || Boolean(error)}>
        {saving ? 'Saving…' : 'Save Coordinator'}
      </button>
    </div>
  )
}

  function OverviewTab({ donorList }) {
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
  function DonorsTab({ caseId, caseStatus, donors, reload, can }) {
    const [adding, setAdding] = useState(false)
    const [donorSearch, setDonorSearch] = useState('')
    const [searchResults, setSearchResults] = useState([])
    const [err, setErr] = useState('')
    const [searchError, setSearchError] = useState('')

    const search = async (q) => {
      setDonorSearch(q)
      setSearchError('')
      if (q.length < 2) { setSearchResults([]); return }
      try {
        const res = await listPatients({ search: q, category: 'donor', page_size: 10 })
        setSearchResults(res.results || [])
      } catch (e) {
        setSearchResults([])
        setSearchError(e.message || 'Could not search donors.')
      }
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
      setErr('')
      try { await updateDonorStatus(donorId, newStatus); reload() }
      catch (e) { setErr(e.message || 'Could not update donor status.') }
    }

    const handleAboCheck = async (donorId) => {
      setErr('')
      try { await checkABO(donorId); reload() }
      catch (e) { setErr(e.message || 'Could not check ABO compatibility.') }
    }

    return (
      <div className="section-panel">
        <h3>
          Candidate Donors
          {can('transplant.manage') && caseStatus === 'under_evaluation' && (
            <button className="btn btn-primary" onClick={() => setAdding(!adding)}>+ Add Donor</button>
          )}
        </h3>
        {adding && caseStatus === 'under_evaluation' && (
          <div style={{ marginBottom: '1rem', padding: '1rem', border: '1px solid #e5e7eb', borderRadius: 8 }}>
            <input type="text" placeholder="Search donors by name or MRN…" value={donorSearch} onChange={(e) => search(e.target.value)} className="input" style={{ width: '100%', marginBottom: 8 }} />
            {searchError && <p className="error-text">{searchError}</p>}
            {searchResults.map((p) => (
              <div key={p.id} style={{ padding: '0.4rem 0.5rem', cursor: 'pointer', borderBottom: '1px solid #f3f4f6' }} onClick={() => addDonor(p.id)}>
                {p.mrn} · {p.full_name}
              </div>
            ))}
            {err && <p className="error-text">{err}</p>}
          </div>
        )}
        {err && !adding && <p className="error-text">{err}</p>}
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
  function ChecklistTab({ caseId, recipient, donors, items, reload, can }) {
    const [adding, setAdding] = useState(false)
    const [form, setForm] = useState({ item_name: '', item_type: 'lab_test', patient: '', is_required: true })
    const [err, setErr] = useState('')
    const patientOptions = [
      recipient,
      ...donors.map((entry) => entry.donor_detail),
    ].filter(Boolean)

    const handleAdd = async () => {
      setErr('')
      if (!form.item_name || !form.patient) {
        setErr('Enter an item name and select the recipient or a candidate donor.')
        return
      }
      try {
        await createChecklistItem(caseId, { ...form, case: caseId })
        setAdding(false); setForm({ item_name: '', item_type: 'lab_test', patient: '', is_required: true })
        reload()
      } catch (e) { setErr(e.message || 'Could not add the checklist item.') }
    }

    const toggleStatus = async (item, newStatus) => {
      setErr('')
      try { await updateChecklistStatus(item.id, newStatus); reload() }
      catch (e) { setErr(e.message || 'Could not update the checklist item.') }
    }

    const handleDelete = async (id) => {
      setErr('')
      try { await deleteChecklistItem(id); reload() }
      catch (e) { setErr(e.message || 'Could not delete the checklist item.') }
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
                <label htmlFor="checklist-patient-picker">Recipient or Donor</label>
                <select
                  id="checklist-patient-picker"
                  value={form.patient}
                  onChange={(e) => setForm({ ...form, patient: e.target.value })}
                  className="input"
                >
                  <option value="">— Select a patient —</option>
                  {patientOptions.map((patient) => (
                    <option key={patient.id} value={patient.id}>
                      {patient.full_name} · {patient.mrn}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label><input type="checkbox" checked={form.is_required} onChange={(e) => setForm({ ...form, is_required: e.target.checked })} /> Required</label>
              </div>
            </div>
            {err && <p className="error-text">{err}</p>}
            <button className="btn btn-primary" onClick={handleAdd} style={{ marginTop: 8 }}>Add Item</button>
          </div>
        )}
        {err && !adding && <p className="error-text">{err}</p>}
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
    const [members, setMembers] = useState([])
    const [staffOptions, setStaffOptions] = useState([])
    const [staffError, setStaffError] = useState('')
    const [err, setErr] = useState('')

    useEffect(() => {
      let active = true
      listTransplantStaff().then(
        (results) => active && setStaffOptions(results),
        (error) => active && setStaffError(error.message || 'Could not load committee members.'),
      )
      return () => { active = false }
    }, [])

    const submit = async () => {
      setErr('')
      const incompleteMember = members.some((member) => !member.staff_id)
      if (incompleteMember) {
        setErr('Choose a staff member for every committee vote row, or remove the empty row.')
        return
      }
      try {
        const payload = {
          ...form,
          members: members.map((member) => ({
            staff_id: Number(member.staff_id),
            vote: member.vote || null,
          })),
        }
        await createDecision(caseId, payload)
        setAdding(false)
        setForm({ meeting_date: '', decision: '', reasons: '', extra_tests: '' })
        setMembers([])
        reload(); reloadCase()
      } catch (e) { setErr(e.message || 'Could not save the committee decision.') }
    }

    const committeeStaff = staffOptions.filter((staff) =>
      !['super_admin', 'billing_admin'].includes(staff.job_title),
    )

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
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Committee Members and Votes</label>
                {members.map((member, index) => (
                  <div className="form-grid" key={index} style={{ marginBottom: 8 }}>
                    <select
                      aria-label={`Committee member ${index + 1}`}
                      value={member.staff_id}
                      onChange={(e) => setMembers(members.map((row, rowIndex) => rowIndex === index ? { ...row, staff_id: e.target.value } : row))}
                      disabled={Boolean(staffError)}
                    >
                      <option value="">— Select staff —</option>
                      {committeeStaff.map((staff) => (
                        <option key={staff.id} value={staff.id}>{staff.name} · {staff.job_title_display}</option>
                      ))}
                    </select>
                    <select
                      aria-label={`Vote for committee member ${index + 1}`}
                      value={member.vote}
                      onChange={(e) => setMembers(members.map((row, rowIndex) => rowIndex === index ? { ...row, vote: e.target.value } : row))}
                    >
                      <option value="">No vote recorded</option>
                      <option value="approve">Approve</option>
                      <option value="reject">Reject</option>
                      <option value="abstain">Abstain</option>
                    </select>
                    <button type="button" className="btn btn-danger" onClick={() => setMembers(members.filter((_, rowIndex) => rowIndex !== index))}>
                      Remove
                    </button>
                  </div>
                ))}
                {staffError && <p className="error-text">{staffError}</p>}
                <button
                  type="button"
                  className="btn"
                  disabled={Boolean(staffError)}
                  onClick={() => setMembers([...members, { staff_id: '', vote: '' }])}
                >
                  Add Committee Member
                </button>
              </div>
            </div>
            <button className="btn btn-primary" onClick={submit} style={{ marginTop: 8 }}>Save Decision</button>
            {err && <p className="error-text">{err}</p>}
          </div>
        )}
        {err && !adding && <p className="error-text">{err}</p>}
        {decisions.map((d) => (
          <div key={d.id} style={{ padding: '1rem', borderBottom: '1px solid #e5e7eb' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong>Decision: <Badge variant={d.decision === 'approved' ? 'success' : d.decision === 'rejected' ? 'danger' : 'warning'}>{d.decision || 'Pending'}</Badge></strong>
              <small>{d.meeting_date} · by {d.recorded_by_detail?.name}</small>
            </div>
            <p style={{ margin: '0.5rem 0' }}>{d.reasons}</p>
            {d.extra_tests && <p><strong>Extra tests:</strong> {d.extra_tests}</p>}
            {d.members?.length > 0 && (
              <small>Members: {d.members.map((m) => `${m.staff_detail?.name || `Staff #${m.staff}`} (${m.vote || 'no vote'})`).join(', ')}</small>
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
    const [surgeons, setSurgeons] = useState([])
    const [surgeonError, setSurgeonError] = useState('')
    const [staffOptions, setStaffOptions] = useState([])
    const [staffError, setStaffError] = useState('')
    const [err, setErr] = useState('')
    const [teamForm, setTeamForm] = useState({ staff: '', team_role: '' })
    const [teamError, setTeamError] = useState('')
    const [completingId, setCompletingId] = useState(null)
    const [completionForm, setCompletionForm] = useState({
      graft_weight_g: '', duration_min: '', operative_notes: '', complications: '',
    })
    const [completing, setCompleting] = useState(false)

    useEffect(() => {
      let active = true
      listTransplantStaff({ job_title: 'transplant_surgeon' }).then(
        (results) => active && setSurgeons(results),
        (error) => active && setSurgeonError(error.message || 'Could not load transplant surgeons.'),
      )
      listTransplantStaff().then(
        (results) => active && setStaffOptions(results),
        (error) => active && setStaffError(error.message || 'Could not load staff members.'),
      )
      return () => { active = false }
    }, [])

    const approvedDonors = donors.filter((d) => d.status === 'approved')
    const eligibleTeamStaff = staffOptions.filter((staff) =>
      !['super_admin', 'billing_admin'].includes(staff.job_title),
    )

    const scheduleSurgery = async () => {
      setErr('')
      if (!form.case_donor || !form.lead_surgeon || !form.scheduled_at) {
        setErr('Select an approved donor and lead surgeon, and enter a scheduled date and time.')
        return
      }
      try {
        await createSurgery(caseId, {
          ...form,
          case: Number(caseId),
          case_donor: Number(form.case_donor),
          lead_surgeon: Number(form.lead_surgeon),
        })
        setAdding(false); reload(); reloadCase()
      } catch (e) { setErr(e.message || 'Could not schedule surgery.') }
    }

    const handleComplete = (surgeryId) => {
      setCompletionForm({ graft_weight_g: '', duration_min: '', operative_notes: '', complications: '' })
      setErr('')
      setCompletingId(surgeryId)
    }

    const submitCompletion = async (event) => {
      event.preventDefault()
      setCompleting(true)
      setErr('')
      const payload = { ...completionForm }
      if (payload.graft_weight_g === '') delete payload.graft_weight_g
      if (payload.duration_min === '') delete payload.duration_min
      try {
        await completeSurgery(completingId, payload)
        setCompletingId(null)
        reload(); reloadCase()
      } catch (e) {
        setErr(e.message || 'Could not complete the surgery.')
      } finally {
        setCompleting(false)
      }
    }

    const handleAddTeamMember = async (surgeryId) => {
      setTeamError('')
      if (!teamForm.staff || !teamForm.team_role.trim()) {
        setTeamError('Select a staff member and enter their surgical role.')
        return
      }
      try {
        await addTeamMember(surgeryId, {
          staff: Number(teamForm.staff),
          team_role: teamForm.team_role.trim(),
        })
        setTeamForm({ staff: '', team_role: '' })
        reload()
      } catch (e) {
        setTeamError(Object.values(fieldErrors(e)).join(' ') || e.message || 'Could not add the surgical team member.')
      }
    }

    const handleRemoveTeamMember = async (memberId) => {
      setTeamError('')
      try {
        await removeTeamMember(memberId)
        reload()
      } catch (e) {
        setTeamError(e.message || 'Could not remove the surgical team member.')
      }
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
                  {approvedDonors.map((d) => <option key={d.id} value={d.id}>{d.donor_detail?.full_name} · {d.donor_detail?.mrn}</option>)}
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
                <label htmlFor="lead-surgeon-picker">Lead Surgeon</label>
                <select
                  id="lead-surgeon-picker"
                  value={form.lead_surgeon}
                  onChange={(e) => setForm({ ...form, lead_surgeon: e.target.value })}
                  disabled={Boolean(surgeonError)}
                >
                  <option value="">— Select a surgeon —</option>
                  {surgeons.map((surgeon) => (
                    <option key={surgeon.id} value={surgeon.id}>
                      {surgeon.name}{surgeon.department ? ` · ${surgeon.department}` : ''}
                    </option>
                  ))}
                </select>
                {surgeonError && <small className="error-text">{surgeonError}</small>}
              </div>
            </div>
            {err && <p className="error-text">{err}</p>}
            <button className="btn btn-primary" onClick={scheduleSurgery} style={{ marginTop: 8 }}>Schedule Surgery</button>
          </div>
        )}
        {err && !adding && <p className="error-text">{err}</p>}
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
            <div className="section-panel" style={{ marginTop: 12 }}>
              <h4>Surgical Team</h4>
              {s.team_members?.length > 0 ? (
                <ul>
                  {s.team_members.map((member) => (
                    <li key={member.id}>
                      {member.staff_detail?.name || 'Staff member'} — {member.team_role}
                      {can('transplant.record_surgery') && (
                        <button className="btn btn-danger" onClick={() => handleRemoveTeamMember(member.id)} style={{ marginLeft: 8 }}>
                          Remove
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              ) : <p>No surgical team members assigned.</p>}
              {can('transplant.record_surgery') && !['completed', 'cancelled'].includes(s.status) && (
                <div className="form-grid">
                  <div className="form-group">
                    <label htmlFor={`team-staff-${s.id}`}>Staff Member</label>
                    <select
                      id={`team-staff-${s.id}`}
                      value={teamForm.staff}
                      onChange={(e) => setTeamForm({ ...teamForm, staff: e.target.value })}
                      disabled={Boolean(staffError)}
                    >
                      <option value="">— Select staff —</option>
                      {eligibleTeamStaff.map((member) => (
                        <option key={member.id} value={member.id}>{member.name} · {member.job_title_display}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label htmlFor={`team-role-${s.id}`}>Surgical Role</label>
                    <input
                      id={`team-role-${s.id}`}
                      value={teamForm.team_role}
                      onChange={(e) => setTeamForm({ ...teamForm, team_role: e.target.value })}
                      placeholder="Assistant surgeon, anesthesiologist…"
                    />
                  </div>
                  <button className="btn" onClick={() => handleAddTeamMember(s.id)} disabled={Boolean(staffError)}>
                    Add Team Member
                  </button>
                </div>
              )}
              {staffError && <p className="error-text">{staffError}</p>}
              {teamError && <p className="error-text">{teamError}</p>}
            </div>
            {can('transplant.record_surgery') && s.status === 'scheduled' && (
              <button className="btn btn-success" onClick={() => handleComplete(s.id)} style={{ marginTop: 8 }}>Complete Surgery</button>
            )}
            {can('transplant.record_surgery') && s.status === 'in_progress' && (
              <button className="btn btn-success" onClick={() => handleComplete(s.id)} style={{ marginTop: 8 }}>Complete Surgery</button>
            )}
          </div>
        ))}
        {surgeries.length === 0 && <p>No surgery records yet.</p>}
        {completingId && (
          <div className="modal-overlay" onClick={() => setCompletingId(null)}>
            <div className="modal-box" onClick={(event) => event.stopPropagation()}>
              <h3>Record Surgery Completion</h3>
              <form onSubmit={submitCompletion}>
                <div className="form-grid">
                  <div className="form-group">
                    <label>Graft weight (g)</label>
                    <input type="number" min="0.01" step="0.01" value={completionForm.graft_weight_g}
                      onChange={(e) => setCompletionForm({ ...completionForm, graft_weight_g: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label>Duration (minutes)</label>
                    <input type="number" min="1" step="1" value={completionForm.duration_min}
                      onChange={(e) => setCompletionForm({ ...completionForm, duration_min: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label>Operative Notes</label>
                    <textarea rows={3} value={completionForm.operative_notes}
                      onChange={(e) => setCompletionForm({ ...completionForm, operative_notes: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label>Complications</label>
                    <textarea rows={3} value={completionForm.complications}
                      onChange={(e) => setCompletionForm({ ...completionForm, complications: e.target.value })} />
                  </div>
                </div>
                {err && <p className="error-text">{err}</p>}
                <div className="form-actions">
                  <button type="submit" className="btn btn-success" disabled={completing}>
                    {completing ? 'Saving…' : 'Save and Complete'}
                  </button>
                  <button type="button" className="btn" onClick={() => setCompletingId(null)}>Cancel</button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    )
  }
