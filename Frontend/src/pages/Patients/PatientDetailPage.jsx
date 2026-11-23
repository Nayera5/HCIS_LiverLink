import { useCallback, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { changePatientCategory, getPatient, updatePatient } from '../../api/patients'
import { useAuth } from '../../auth/authContext'
import { JOB_TITLE_LABELS } from '../../auth/roles'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { ConfirmDialog, LoadingBlock } from '../../components/ui/Feedback'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import { useApi } from '../../hooks/useApi'
import { formatDate, formatDateTime } from '../../utils/format'
import PatientLabResultsPanel from '../Labs/PatientLabResultsPanel'
import PatientMedicationsPanel from '../Prescriptions/PatientMedicationsPanel'
import PatientTreatmentPlansPanel from '../Prescriptions/PatientTreatmentPlansPanel'
import ConsentsPanel from '../Consents/ConsentsPanel'
import PatientForm from './PatientForm'
import { ageSex, CATEGORY_LABELS, CATEGORY_OPTIONS, categoryBadge, patientName } from './patientDisplay'
import './Patients.css'

const show = (value, suffix = '') => (value === null || value === undefined || value === '' ? '—' : `${value}${suffix}`)

function CategoryPanel({ patient, onChanged }) {
  const [choice, setChoice] = useState(patient.category)
  const [confirming, setConfirming] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const apply = async () => {
    setSaving(true)
    setError('')
    try {
      const updated = await changePatientCategory(patient.id, choice)
      onChanged(updated, `Category changed to ${CATEGORY_LABELS[updated.category]}.`)
      setConfirming(false)
    } catch (err) {
      setError(getErrorMessage(err, 'Could not change the category.'))
      setConfirming(false)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Panel title="Patient category" subtitle="A person can move between categories over time.">
      {error && <Alert variant="error" className="form-alert">{error}</Alert>}
      <div className="category-control">
        <SelectField label="Category" name="category" value={choice} options={CATEGORY_OPTIONS}
          onChange={(event) => setChoice(event.target.value)} />
        <Button variant="secondary" disabled={choice === patient.category} onClick={() => setConfirming(true)}>
          Change category
        </Button>
      </div>
      <ConfirmDialog open={confirming} title="Change patient category?" confirmLabel="Change category"
        busy={saving} onConfirm={apply} onCancel={() => setConfirming(false)}>
        {patientName(patient)} ({patient.mrn}) will change from{' '}
        <strong>{CATEGORY_LABELS[patient.category]}</strong> to <strong>{CATEGORY_LABELS[choice]}</strong>.
        This change is recorded in the audit log.
      </ConfirmDialog>
    </Panel>
  )
}

export default function PatientDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const { can } = useAuth()
  const loader = useCallback(() => getPatient(id), [id])
  const { data: patient, error, loading, setData } = useApi(loader)
  const [flash, setFlash] = useState(location.state?.flash || '')
  const [editing, setEditing] = useState(false)
  const [categoryKey, setCategoryKey] = useState(0)

  if (loading && !patient) return <LoadingBlock label="Loading patient" />
  if (error && !patient) {
    return (
      <>
        <PageHeader back={{ to: '/patients', label: 'Patients' }} title="Patient" />
        <Alert variant="error">{getErrorMessage(error, 'Could not load this patient.')}</Alert>
      </>
    )
  }

  const canEdit = can('patients.edit')
  const canChangeCategory = can('patients.change_category')
  const canViewConsents = can('consents.view') // not Super Admin or Billing Admin

  const save = async (payload) => {
    const updated = await updatePatient(patient.id, payload)
    setData(updated)
    setEditing(false)
    setFlash('Patient details saved.')
  }

  return (
    <>
      <PageHeader
        back={{ to: '/patients', label: 'Patients' }}
        eyebrow="Patient profile"
        title={patientName(patient)}
        actions={!editing && (canEdit || can('emr.view')) && (
          <>
            {can('emr.view') && (
              <Button as={Link} to={`/patients/${patient.id}/medical-record`}>Open medical record</Button>
            )}
            {canEdit && (
              <Button variant="secondary" onClick={() => { setEditing(true); setFlash('') }}>Edit demographics</Button>
            )}
          </>
        )}
      />
      <div className="patient-summary">
        <span className="patient-summary__mrn">{patient.mrn}</span>
        <span className="muted-text">· {ageSex(patient)}</span>
        {categoryBadge(patient.category)}
        {patient.has_account ? <Badge tone="info">Portal account</Badge> : <Badge>No portal account</Badge>}
      </div>

      <div className="content-stack">
        {flash && <Alert variant="success">{flash}</Alert>}

        {editing ? (
          <Panel title="Edit demographics" subtitle="MRN and category cannot be changed here.">
            <PatientForm initial={patient} submitLabel="Save changes" onSubmit={save}
              onCancel={() => setEditing(false)} />
          </Panel>
        ) : (
          <div className="content-grid">
            <div className="content-stack">
              <Panel title="Demographic profile">
                <dl className="detail-list">
                  <div><dt>First name</dt><dd>{patient.first_name}</dd></div>
                  <div><dt>Family name</dt><dd>{patient.last_name}</dd></div>
                  <div><dt>Date of birth</dt><dd>{formatDate(patient.date_of_birth)} ({patient.age} years)</dd></div>
                  <div><dt>Sex</dt><dd>{patient.sex === 'female' ? 'Female' : 'Male'}</dd></div>
                  <div><dt>National ID</dt><dd>{show(patient.national_id)}</dd></div>
                  <div><dt>MRN</dt><dd>{patient.mrn}</dd></div>
                </dl>
              </Panel>
              <Panel title="Contact">
                <dl className="detail-list">
                  <div><dt>Phone</dt><dd>{patient.phone}</dd></div>
                  <div><dt>Emergency contact</dt><dd>{show(patient.emergency_contact)}</dd></div>
                  <div><dt>Address</dt><dd>{show(patient.address)}</dd></div>
                </dl>
              </Panel>
            </div>
            <div className="content-stack">
              <Panel title="Clinical basics">
                <dl className="detail-list">
                  <div><dt>Blood group</dt><dd>{show(patient.blood_group)}</dd></div>
                  <div><dt>Height</dt><dd>{show(patient.height_cm, ' cm')}</dd></div>
                  <div><dt>Weight</dt><dd>{show(patient.weight_kg, ' kg')}</dd></div>
                </dl>
                {!patient.weight_kg && (
                  <p className="muted-text panel-note">Weight is required before a GRWR check can run.</p>
                )}
              </Panel>
              {canChangeCategory && (
                <CategoryPanel key={`${patient.category}-${categoryKey}`} patient={patient}
                  onChanged={(updated, message) => {
                    setData(updated)
                    setCategoryKey((k) => k + 1)
                    setFlash(message)
                  }} />
              )}
              {canViewConsents && <ConsentsPanel patient={patient} />}
              <Panel title="Registration">
                <dl className="detail-list">
                  <div>
                    <dt>Registered by</dt>
                    <dd>
                      {patient.registered_by
                        ? `${patient.registered_by.name} (${JOB_TITLE_LABELS[patient.registered_by.job_title] || patient.registered_by.job_title})`
                        : patient.has_account ? 'Self-registered (portal)' : '—'}
                    </dd>
                  </div>
                  <div><dt>Registered on</dt><dd>{formatDateTime(patient.created_at)}</dd></div>
                  <div><dt>Last updated</dt><dd>{formatDateTime(patient.updated_at)}</dd></div>
                </dl>
              </Panel>
            </div>
          </div>
        )}
        {!editing && can('prescriptions.view') && <PatientMedicationsPanel patientId={patient.id} />}
        {!editing && can('treatment_plans.view') && <PatientTreatmentPlansPanel patientId={patient.id} />}
        {!editing && can('labs.view') && <PatientLabResultsPanel patientId={patient.id} />}
      </div>
    </>
  )
}
