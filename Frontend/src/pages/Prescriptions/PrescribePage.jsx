import { useCallback, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import { getPatient } from '../../api/patients'
import { createPrescription } from '../../api/prescriptions'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { LoadingBlock } from '../../components/ui/Feedback'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextAreaField from '../../components/ui/TextAreaField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { ageSex, patientName } from '../Patients/patientDisplay'
import DrugAutocomplete from './DrugAutocomplete'
import { addDays, daysBetween, FREQUENCY_SUGGESTIONS, ROUTE_OPTIONS, todayIso, validatePrescription } from './rxFormat'
import './Prescriptions.css'

function PrescriptionForm({ patient }) {
  const navigate = useNavigate()
  const [drug, setDrug] = useState(null)
  const [form, setForm] = useState({
    dose: '', route: '', frequency: '', start_date: todayIso(), duration_days: '', end_date: '', instructions: '',
  })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  const set = (key) => (event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))

  // Duration and end date are two views of the same thing: editing one updates the other.
  const setDuration = (event) => {
    const value = event.target.value
    setForm((prev) => {
      const n = Number(value)
      const end = value && Number.isInteger(n) && n > 0 && prev.start_date ? addDays(prev.start_date, n) : prev.end_date
      return { ...prev, duration_days: value, end_date: value ? end : '' }
    })
  }
  const setEnd = (event) => {
    const end = event.target.value
    setForm((prev) => {
      const days = end && prev.start_date ? daysBetween(prev.start_date, end) : ''
      return { ...prev, end_date: end, duration_days: days !== '' && days > 0 ? String(days) : '' }
    })
  }
  const setStart = (event) => {
    const start = event.target.value
    setForm((prev) => {
      const n = Number(prev.duration_days)
      return { ...prev, start_date: start, end_date: start && n > 0 ? addDays(start, n) : prev.end_date }
    })
  }

  const chooseDrug = (picked) => {
    setDrug(picked)
    if (picked?.default_route) setForm((prev) => (prev.route ? prev : { ...prev, route: picked.default_route }))
  }

  const submit = async (event) => {
    event.preventDefault()
    const found = validatePrescription({ ...form, drug: drug?.id })
    setErrors(found)
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      await createPrescription({
        patient: patient.id, drug: drug.id, dose: form.dose.trim(), route: form.route,
        frequency: form.frequency.trim(), start_date: form.start_date, end_date: form.end_date || null,
        instructions: form.instructions.trim(),
      })
      navigate(`/patients/${patient.id}`, { state: { flash: `${drug.name} prescribed.` } })
    } catch (err) {
      const fields = fieldErrors(err)
      setErrors(Object.keys(fields).length ? fields : { form: getErrorMessage(err, 'Could not save the prescription.') })
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate className="content-stack">
      {errors.form && <Alert variant="error">{errors.form}</Alert>}
      <Panel title="Medication">
        <div className="form-stack">
          <DrugAutocomplete value={drug} onChange={chooseDrug} error={errors.drug} />
          <div className="rx-grid">
            <TextField label="Dose per intake" value={form.dose} onChange={set('dose')} error={errors.dose}
              placeholder={drug?.common_dose ? `e.g. ${drug.common_dose}` : 'e.g. 300 mg'} />
            <SelectField label="Route" placeholder="Choose…" options={ROUTE_OPTIONS} value={form.route}
              onChange={set('route')} error={errors.route} />
            <TextField label="Frequency" value={form.frequency} onChange={set('frequency')} error={errors.frequency}
              list="rx-frequencies" placeholder="e.g. twice daily" />
            <datalist id="rx-frequencies">
              {FREQUENCY_SUGGESTIONS.map((f) => <option key={f} value={f} />)}
            </datalist>
          </div>
        </div>
      </Panel>
      <Panel title="Duration" subtitle="Leave the duration and end date empty for an ongoing medication.">
        <div className="rx-grid">
          <TextField label="Start date" type="date" value={form.start_date} onChange={setStart} error={errors.start_date} />
          <TextField label="Duration (days)" type="number" min="1" step="1" inputMode="numeric"
            value={form.duration_days} onChange={setDuration} error={errors.duration_days} />
          <TextField label="End date" type="date" value={form.end_date} min={form.start_date ? addDays(form.start_date, 1) : undefined}
            onChange={setEnd} error={errors.end_date} hint={form.end_date ? '' : 'Ongoing'} />
        </div>
      </Panel>
      <Panel title="Instructions">
        <TextAreaField label="Instructions for the patient" optional value={form.instructions}
          onChange={set('instructions')} placeholder="e.g. take with food; check trough level in 1 week" />
      </Panel>
      <div className="form-actions">
        <Button as={Link} to={`/patients/${patient.id}`} variant="secondary">Cancel</Button>
        <Button type="submit" loading={saving}>Prescribe</Button>
      </div>
    </form>
  )
}

/** /rx/new?patient=<id>  E-prescription (doctors only: prescriptions.prescribe). */
export default function PrescribePage() {
  const [searchParams] = useSearchParams()
  const patientId = searchParams.get('patient')
  const loader = useCallback(() => (patientId ? getPatient(patientId) : Promise.resolve(null)), [patientId])
  const { data: patient, error, loading } = useApi(loader)

  return (
    <>
      <PageHeader back={patientId ? { to: `/patients/${patientId}`, label: 'Patient profile' } : { to: '/patients', label: 'Patients' }}
        eyebrow="Prescriptions" title="New prescription" />
      {!patientId ? (
        <Alert variant="info">
          Open a patient’s profile from <Link to="/patients">Patients</Link> and choose “Prescribe”.
        </Alert>
      ) : loading && !patient ? (
        <LoadingBlock label="Loading patient" />
      ) : error ? (
        <Alert variant="error">{getErrorMessage(error, 'Could not load this patient.')}</Alert>
      ) : patient ? (
        <div className="content-stack">
          <div className="patient-summary">
            <span className="patient-summary__mrn">{patientName(patient)}</span>
            <span className="muted-text">· {patient.mrn} · {ageSex(patient)}</span>
          </div>
          <PrescriptionForm patient={patient} />
        </div>
      ) : null}
    </>
  )
}
