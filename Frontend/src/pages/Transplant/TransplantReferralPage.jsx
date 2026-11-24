/* New Transplant Referral – create a new case. */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../../components/ui/PageHeader'
import { createReferral, listTransplantStaff } from '../../api/transplant'
import { listPatients } from '../../api/patients'
import { fieldErrors } from '../../api/http'
import './Transplant.css'

export default function TransplantReferralPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ recipient: '', referral_date: new Date().toISOString().slice(0, 10), coordinator: '' })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [patientSearch, setPatientSearch] = useState('')
  const [patients, setPatients] = useState([])
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [coordinators, setCoordinators] = useState([])
  const [coordinatorError, setCoordinatorError] = useState('')

  useEffect(() => {
    let active = true
    listTransplantStaff({ job_title: 'transplant_coordinator' }).then(
      (results) => active && setCoordinators(results),
      (err) => active && setCoordinatorError(err.message || 'Could not load coordinators.'),
    )
    return () => { active = false }
  }, [])

  const searchPatients = async (q) => {
    setPatientSearch(q)
    setForm((current) => ({ ...current, recipient: '' }))
    setSearchError('')
    if (q.length < 2) { setPatients([]); return }
    setSearching(true)
    try {
      const res = await listPatients({ search: q, page_size: 10 })
      setPatients(res.results || [])
    } catch (err) {
      setPatients([])
      setSearchError(err.message || 'Could not search patients.')
    } finally {
      setSearching(false)
    }
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!form.recipient) { setErrors({ recipient: 'Select a patient.' }); return }
    setSaving(true)
    setErrors({})
    try {
      const data = { recipient: form.recipient, referral_date: form.referral_date }
      if (form.coordinator) data.coordinator = Number(form.coordinator)
      const result = await createReferral(data)
      navigate(`/transplant/cases/${result.id}`)
    } catch (err) {
      setErrors(fieldErrors(err))
      setSaving(false)
    }
  }

  return (
    <div className="transplant-page">
      <PageHeader title="New Transplant Referral" />
      <div className="section-panel" style={{ maxWidth: 600 }}>
        <form onSubmit={submit}>
          <div className="form-grid">
            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label>Recipient (search by name or MRN)</label>
              <input
                type="text" placeholder="Type to search…"
                value={patientSearch} onChange={(e) => searchPatients(e.target.value)}
                className="input"
              />
              {searching && <small>Searching…</small>}
              {searchError && <small className="error-text">{searchError}</small>}
              {patients.length > 0 && (
                <div style={{ border: '1px solid #e5e7eb', borderRadius: 6, maxHeight: 200, overflow: 'auto', marginTop: 4 }}>
                  {patients.map((p) => (
                    <div
                      key={p.id}
                      style={{ padding: '0.5rem 0.75rem', cursor: 'pointer', background: form.recipient === p.id ? '#eff6ff' : '' }}
                      onClick={() => { setForm({ ...form, recipient: p.id }); setPatientSearch(`${p.mrn} · ${p.full_name}`); setPatients([]) }}
                    >
                      <strong>{p.mrn}</strong> · {p.full_name} ({p.category})
                    </div>
                  ))}
                </div>
              )}
              {errors.recipient && <small className="error-text">{errors.recipient}</small>}
            </div>
            <div className="form-group">
              <label>Referral Date</label>
              <input type="date" value={form.referral_date} onChange={(e) => setForm({ ...form, referral_date: e.target.value })} />
            </div>
            <div className="form-group">
              <label htmlFor="coordinator-picker">Coordinator (optional)</label>
              <select
                id="coordinator-picker"
                value={form.coordinator}
                onChange={(e) => setForm({ ...form, coordinator: e.target.value })}
                disabled={Boolean(coordinatorError)}
              >
                <option value="">Unassigned</option>
                {coordinators.map((member) => (
                  <option key={member.id} value={member.id}>
                    {member.name}{member.department ? ` · ${member.department}` : ''}
                  </option>
                ))}
              </select>
              {coordinatorError && <small className="error-text">{coordinatorError}</small>}
            </div>
          </div>
          {errors.form && <p className="error-text">{errors.form}</p>}
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Creating…' : 'Create Referral'}
            </button>
            <button type="button" className="btn" onClick={() => navigate('/transplant')}>Cancel</button>
          </div>
        </form>
      </div>
    </div>
  )
}
