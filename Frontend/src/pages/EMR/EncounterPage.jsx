import { useCallback, useState } from 'react'
import { useLocation, useParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import {
  addAddendum, createDiagnosis, createVitals, deleteDiagnosis, deleteVitals, getEncounter, signEncounter,
  updateDiagnosis, updateEncounter,
} from '../../api/emr'
import { fieldErrors } from '../../api/http'
import { getPatient } from '../../api/patients'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { ConfirmDialog, LoadingBlock } from '../../components/ui/Feedback'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { ImagingOrdersPanel } from '../Imaging/imagingParts'
import { patientName } from '../Patients/patientDisplay'
import { TextAreaField } from './emrPanels'
import {
  DIAGNOSIS_STATUS, ENCOUNTER_STATUS, diagnosisPayload, encounterPayload, formatBp, validateDiagnosis,
  validateEncounter, validateVitals, vitalsPayload,
} from './emrRules'
import Icd10Picker from './Icd10Picker'
import '../Patients/Patients.css'
import './EMR.css'

const show = (value, suffix = '') => (value === null || value === undefined || value === '' ? '—' : `${value}${suffix}`)

/** Small form helper: validate, send, map backend 400 errors. */
function useSubmit(fallback) {
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const submit = async (found, send) => {
    setErrors(found)
    if (Object.keys(found).length) return false
    setSaving(true)
    try {
      await send()
      return true
    } catch (error) {
      const { form, ...rest } = fieldErrors(error)
      setErrors({ ...rest, form: form || (Object.keys(rest).length ? '' : getErrorMessage(error, fallback)) })
      return false
    } finally {
      setSaving(false)
    }
  }
  return { errors, saving, submit }
}

// ---------------------------------------------------------------------------- Notes
function NotesPanel({ encounter, editable, onSaved }) {
  const [editing, setEditing] = useState(false)
  const [values, setValues] = useState({
    chief_complaint: encounter.chief_complaint, clinical_notes: encounter.clinical_notes,
  })
  const { errors, saving, submit } = useSubmit('Could not save the notes.')
  const change = (event) => setValues((prev) => ({ ...prev, [event.target.name]: event.target.value }))

  const save = async (event) => {
    event.preventDefault()
    const ok = await submit(validateEncounter(values),
      () => updateEncounter(encounter.encounter_id, encounterPayload(values)))
    if (ok) {
      setEditing(false)
      onSaved()
    }
  }

  return (
    <Panel title="Clinical notes"
      action={editable && !editing && <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>Edit</Button>}>
      {editing ? (
        <form onSubmit={save} noValidate className="form-stack">
          {errors.form && <Alert variant="error">{errors.form}</Alert>}
          <TextField label="Chief complaint" name="chief_complaint" value={values.chief_complaint}
            onChange={change} error={errors.chief_complaint} />
          <TextAreaField label="Clinical notes" name="clinical_notes" value={values.clinical_notes}
            onChange={change} rows={8} error={errors.clinical_notes} />
          <div className="form-actions">
            <Button variant="secondary" onClick={() => setEditing(false)}>Cancel</Button>
            <Button type="submit" loading={saving}>Save notes</Button>
          </div>
        </form>
      ) : (
        <dl className="detail-list">
          <div><dt>Chief complaint</dt><dd>{show(encounter.chief_complaint)}</dd></div>
          <div><dt>Notes</dt><dd className="emr-pre">{show(encounter.clinical_notes)}</dd></div>
        </dl>
      )}
    </Panel>
  )
}

// ---------------------------------------------------------------------------- Vital signs
const EMPTY_VITALS = { bp_systolic: '', bp_diastolic: '', pulse: '', temperature: '', weight_kg: '', height_cm: '' }

function VitalsPanel({ encounter, editable, onChanged }) {
  const [adding, setAdding] = useState(false)
  const [values, setValues] = useState(EMPTY_VITALS)
  const [actionError, setActionError] = useState('')
  const { errors, saving, submit } = useSubmit('Could not save the vital signs.')
  const change = (event) => setValues((prev) => ({ ...prev, [event.target.name]: event.target.value }))
  const field = (name, label, step = '1') => (
    <TextField label={label} name={name} type="number" inputMode="decimal" min="0" step={step}
      value={values[name]} onChange={change} error={errors[name]} />
  )

  const save = async (event) => {
    event.preventDefault()
    const ok = await submit(validateVitals(values), () => createVitals(vitalsPayload(values, encounter.encounter_id)))
    if (ok) {
      setAdding(false)
      setValues(EMPTY_VITALS)
      onChanged()
    }
  }

  const remove = async (vitals) => {
    setActionError('')
    try {
      await deleteVitals(vitals.vitals_id)
      onChanged()
    } catch (err) {
      setActionError(getErrorMessage(err, 'Could not delete the reading.'))
    }
  }

  const rows = encounter.vital_signs
  return (
    <Panel title="Vital signs" subtitle="BMI is calculated from weight and height."
      flush={rows.length > 0 && !adding && !actionError}
      action={editable && !adding && <Button size="sm" variant="secondary" onClick={() => setAdding(true)}>Add reading</Button>}>
      {actionError && <Alert variant="error" className="form-alert">{actionError}</Alert>}
      {adding && (
        <form onSubmit={save} noValidate className="form-stack emr-form">
          {errors.form && <Alert variant="error">{errors.form}</Alert>}
          <div className="form-grid">
            {field('bp_systolic', 'Systolic (mmHg)')}
            {field('bp_diastolic', 'Diastolic (mmHg)')}
            {field('pulse', 'Pulse (bpm)')}
            {field('temperature', 'Temperature (°C)', '0.1')}
            {field('weight_kg', 'Weight (kg)', '0.01')}
            {field('height_cm', 'Height (cm)', '0.1')}
          </div>
          <div className="form-actions">
            <Button variant="secondary" onClick={() => setAdding(false)}>Cancel</Button>
            <Button type="submit" loading={saving}>Save reading</Button>
          </div>
        </form>
      )}
      {rows.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Taken</th>
                <th scope="col">BP</th>
                <th scope="col">Pulse</th>
                <th scope="col" className="hide-sm">Temp.</th>
                <th scope="col" className="hide-sm">Weight</th>
                <th scope="col" className="hide-sm">Height</th>
                <th scope="col">BMI</th>
                {editable && <th scope="col"><span className="visually-hidden">Actions</span></th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((v) => (
                <tr key={v.vitals_id}>
                  <td>{formatDateTime(v.recorded_at)}</td>
                  <td>{formatBp(v)}</td>
                  <td>{show(v.pulse)}</td>
                  <td className="hide-sm">{show(v.temperature, ' °C')}</td>
                  <td className="hide-sm">{show(v.weight_kg, ' kg')}</td>
                  <td className="hide-sm">{show(v.height_cm, ' cm')}</td>
                  <td>{show(v.bmi)}</td>
                  {editable && (
                    <td className="cell-actions">
                      <Button size="sm" variant="link" onClick={() => remove(v)}>Delete</Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : !adding && <p className="muted-text">No vital signs recorded.</p>}
    </Panel>
  )
}

// ---------------------------------------------------------------------------- Diagnoses
const EMPTY_DIAGNOSIS = { icd10: null, is_primary: false }

function DiagnosesPanel({ encounter, editable, canWrite, onChanged }) {
  const [adding, setAdding] = useState(false)
  const [values, setValues] = useState(EMPTY_DIAGNOSIS)
  const [actionError, setActionError] = useState('')
  const { errors, saving, submit } = useSubmit('Could not save the diagnosis.')

  const save = async (event) => {
    event.preventDefault()
    const ok = await submit(validateDiagnosis(values, encounter.diagnoses),
      () => createDiagnosis(diagnosisPayload(values, encounter.encounter_id)))
    if (ok) {
      setAdding(false)
      setValues(EMPTY_DIAGNOSIS)
      onChanged()
    }
  }

  const act = async (action, fallback) => {
    setActionError('')
    try {
      await action()
      onChanged()
    } catch (err) {
      setActionError(getErrorMessage(err, fallback))
    }
  }

  return (
    <Panel title="Diagnoses" subtitle="Coded with ICD-10. One primary diagnosis per visit."
      action={editable && !adding && <Button size="sm" variant="secondary" onClick={() => setAdding(true)}>Add diagnosis</Button>}>
      {actionError && <Alert variant="error" className="form-alert">{actionError}</Alert>}
      {adding && (
        <form onSubmit={save} noValidate className="form-stack emr-form">
          {errors.form && <Alert variant="error">{errors.form}</Alert>}
          <Icd10Picker value={values.icd10} error={errors.icd10_code}
            onChange={(icd10) => setValues((prev) => ({ ...prev, icd10 }))} />
          <label className="emr-check">
            <input type="checkbox" name="is_primary" checked={values.is_primary}
              onChange={(event) => setValues((prev) => ({ ...prev, is_primary: event.target.checked }))} />
            Primary diagnosis of this visit
          </label>
          {errors.is_primary && <p className="field__error">{errors.is_primary}</p>}
          <div className="form-actions">
            <Button variant="secondary" onClick={() => setAdding(false)}>Cancel</Button>
            <Button type="submit" loading={saving}>Add diagnosis</Button>
          </div>
        </form>
      )}
      {encounter.diagnoses.length ? (
        <ul className="emr-list">
          {encounter.diagnoses.map((d) => (
            <li key={d.diagnosis_id} className="emr-list__item">
              <div>
                <div className="cell-primary">
                  <span className="emr-code">{d.icd10_code}</span> {d.description}
                </div>
                <div className="emr-badges">
                  {d.is_primary && <Badge tone="teal">Primary</Badge>}
                  <Badge tone={DIAGNOSIS_STATUS[d.status].tone}>{DIAGNOSIS_STATUS[d.status].label}</Badge>
                </div>
              </div>
              {canWrite && (
                <div className="emr-actions">
                  {/* Status can change after signing (active → resolved); coding cannot. */}
                  <Button size="sm" variant="link"
                    onClick={() => act(() => updateDiagnosis(d.diagnosis_id,
                      { status: d.status === 'active' ? 'resolved' : 'active' }), 'Could not change the status.')}>
                    {d.status === 'active' ? 'Mark resolved' : 'Mark active'}
                  </Button>
                  {editable && (
                    <Button size="sm" variant="link"
                      onClick={() => act(() => deleteDiagnosis(d.diagnosis_id), 'Could not delete the diagnosis.')}>
                      Delete
                    </Button>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      ) : !adding && <p className="muted-text">No diagnoses recorded.</p>}
    </Panel>
  )
}

// ---------------------------------------------------------------------------- Addenda
function AddendaPanel({ encounter, canAdd, onChanged }) {
  const [text, setText] = useState('')
  const { errors, saving, submit } = useSubmit('Could not add the addendum.')

  const save = async (event) => {
    event.preventDefault()
    const found = text.trim() ? {} : { text: 'Write the correction or addition.' }
    if (await submit(found, () => addAddendum(encounter.encounter_id, text.trim()))) {
      setText('')
      onChanged()
    }
  }

  if (!encounter.addenda.length && !canAdd) return null
  return (
    <Panel title="Addenda" subtitle="Corrections and additions made after the encounter was signed.">
      {encounter.addenda.length > 0 && (
        <ul className="emr-list">
          {encounter.addenda.map((a) => (
            <li key={a.addendum_id} className="emr-list__item emr-list__item--stacked">
              <div className="emr-pre">{a.text}</div>
              <div className="cell-secondary">{a.author_name} · {formatDateTime(a.created_at)}</div>
            </li>
          ))}
        </ul>
      )}
      {canAdd && (
        <form onSubmit={save} noValidate className="form-stack emr-addendum-form">
          {errors.form && <Alert variant="error">{errors.form}</Alert>}
          <TextAreaField label="New addendum" name="text" value={text} rows={3}
            onChange={(event) => setText(event.target.value)} error={errors.text} />
          <div className="form-actions">
            <Button type="submit" loading={saving}>Add addendum</Button>
          </div>
        </form>
      )}
    </Panel>
  )
}

// ---------------------------------------------------------------------------- Page
/**
 * One encounter. Staff route /encounters/:id (emr.view); portal route
 * /my-medical-record/encounters/:id (self.medical_records, signed encounters only, read-only).
 */
export default function EncounterPage({ portal = false }) {
  const { id } = useParams()
  const location = useLocation()
  const { can } = useAuth()
  const canWrite = !portal && can('emr.write')
  const loader = useCallback(() => getEncounter(id), [id])
  const { data: encounter, error, loading, reload } = useApi(loader)
  // Staff header shows the patient's name; portal users already know who they are.
  const patientId = portal ? null : encounter?.patient
  const patientLoader = useCallback(() => (patientId ? getPatient(patientId) : Promise.resolve(null)), [patientId])
  const { data: patient } = useApi(patientLoader)
  const [flash, setFlash] = useState(location.state?.flash || '')
  const [signing, setSigning] = useState(false)
  const [busy, setBusy] = useState(false)
  const [signError, setSignError] = useState('')

  const back = portal
    ? { to: '/my-medical-record', label: 'My medical record' }
    : { to: encounter ? `/patients/${encounter.patient}/medical-record` : '/patients', label: 'Medical record' }

  if (loading && !encounter) return <LoadingBlock label="Loading encounter" />
  if (error && !encounter) {
    return (
      <>
        <PageHeader back={back} title="Encounter" />
        <Alert variant="error">{getErrorMessage(error, 'Could not load this encounter.')}</Alert>
      </>
    )
  }

  const isOpen = encounter.status === 'open'
  const editable = canWrite && isOpen
  const status = ENCOUNTER_STATUS[encounter.status]

  const confirmSign = async () => {
    setBusy(true)
    setSignError('')
    try {
      await signEncounter(encounter.encounter_id)
      setFlash('Encounter signed. It can now only be changed with an addendum.')
      reload()
    } catch (err) {
      setSignError(getErrorMessage(err, 'Could not sign the encounter.'))
    } finally {
      setBusy(false)
      setSigning(false)
    }
  }

  return (
    <>
      <PageHeader back={back} eyebrow={patient ? `${patientName(patient)} · ${patient.mrn}` : 'Encounter'}
        title={`Visit on ${formatDateTime(encounter.encounter_date)}`}
        actions={canWrite && encounter.can_sign && (
          <Button onClick={() => { setSigning(true); setFlash('') }}>Sign encounter</Button>
        )} />
      <div className="patient-summary">
        <Badge tone={status.tone}>{status.label}</Badge>
        <span className="muted-text">Treating doctor: {encounter.staff_name || '—'}</span>
      </div>

      <div className="content-stack">
        {flash && <Alert variant="success">{flash}</Alert>}
        {signError && <Alert variant="error">{signError}</Alert>}
        {canWrite && isOpen && !encounter.can_sign && (
          <Alert variant="info">Only the treating doctor can sign this encounter.</Alert>
        )}
        <div className="content-grid">
          <div className="content-stack">
            <NotesPanel key={`${encounter.encounter_id}-${encounter.status}`} encounter={encounter}
              editable={editable} onSaved={reload} />
            <VitalsPanel encounter={encounter} editable={editable} onChanged={reload} />
          </div>
          <div className="content-stack">
            <DiagnosesPanel encounter={encounter} editable={editable} canWrite={canWrite} onChanged={reload} />
            {!portal && can('imaging.view') && (
              <ImagingOrdersPanel patientId={encounter.patient} encounterId={encounter.encounter_id} />
            )}
            <AddendaPanel encounter={encounter} canAdd={canWrite && !isOpen} onChanged={reload} />
          </div>
        </div>
      </div>

      <ConfirmDialog open={signing} title="Sign this encounter?" confirmLabel="Sign encounter" busy={busy}
        onConfirm={confirmSign} onCancel={() => setSigning(false)}>
        After signing, the notes, vital signs and diagnosis codes are locked and the visit becomes visible to the
        patient. Later corrections are added as addenda. This is recorded in the audit log.
      </ConfirmDialog>
    </>
  )
}
