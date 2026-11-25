import { useCallback, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { listEncounters } from '../../api/emr'
import { fieldErrors } from '../../api/http'
import { createImagingOrder } from '../../api/imaging'
import { getPatient, listPatients } from '../../api/patients'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { SearchIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextAreaField from '../../components/ui/TextAreaField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { ageSex, categoryBadge, patientName } from '../Patients/patientDisplay'
import {
  ACTIVE_IMAGING_SERVICES, MAX_INDICATION, imagingOrderPayload, imagingServiceOptions, orderOrigin,
  validateImagingOrder,
} from './imagingRules'
import { useImagingServices } from './useImagingServices'
import '../Labs/Labs.css'
import '../Patients/Patients.css'

const visitLabel = (e) => [formatDateTime(e.encounter_date), e.chief_complaint].filter(Boolean).join(' · ')

/** Step 1 when no patient is chosen yet: search the registry and pick one. */
function PatientSearch() {
  const [text, setText] = useState('')
  const [term, setTerm] = useState('')
  const [, setSearchParams] = useSearchParams()
  const loader = useCallback(() => (term ? listPatients({ search: term, page_size: 8 }) : Promise.resolve(null)), [term])
  const { data, error, loading } = useApi(loader)

  return (
    <Panel title="Choose a patient" subtitle="Search by name, MRN, national ID or phone.">
      <form className="form-stack" role="search" onSubmit={(event) => { event.preventDefault(); setTerm(text.trim()) }}>
        <TextField label="Search" name="search" value={text} onChange={(event) => setText(event.target.value)}
          endAdornment={(
            <button type="submit" className="field__icon-button" aria-label="Search patients">
              <SearchIcon size={18} />
            </button>
          )} />
      </form>
      {error && <Alert variant="error" className="form-alert">{getErrorMessage(error, 'Could not search patients.')}</Alert>}
      {loading && !data && <LoadingBlock label="Searching" />}
      {data && (data.results.length ? (
        <ul className="picker-list">
          {data.results.map((patient) => (
            <li key={patient.id}>
              <div>
                <div className="cell-primary">{patientName(patient)}</div>
                <div className="cell-secondary">{patient.mrn} · {ageSex(patient)} {categoryBadge(patient.category)}</div>
              </div>
              <Button variant="secondary" size="sm" onClick={() => setSearchParams({ patient: String(patient.id) })}>
                Select
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title="No patients found">Check the spelling, or register the patient first.</EmptyState>
      ))}
    </Panel>
  )
}

function OrderForm({ patient, encounterId, cancelTo }) {
  const navigate = useNavigate()
  const [values, setValues] = useState({
    billing_service: '', clinical_indication: '', encounter: encounterId,
  })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const loader = useCallback(() => listEncounters({ patient: patient.id }), [patient.id])
  const { data: encounters, error: encountersError } = useApi(loader)
  const { services, error: servicesError, loading: loadingServices, reload: reloadServices } =
    useImagingServices(ACTIVE_IMAGING_SERVICES)

  const linkedVisit = (encounters || []).find((e) => String(e.encounter_id) === encounterId)

  const change = (event) => {
    const { name, value } = event.target
    setValues((prev) => ({ ...prev, [name]: value }))
  }

  const submit = async (event) => {
    event.preventDefault()
    const found = validateImagingOrder(values)
    setErrors(found)
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      const order = await createImagingOrder(imagingOrderPayload(values, patient.id))
      navigate(`/imaging/orders/${order.imaging_order_id}`, { state: { flash: 'Imaging order placed.' } })
    } catch (err) {
      const { form, ...rest } = fieldErrors(err)
      const message = form || rest.patient
        || (Object.keys(rest).length ? '' : getErrorMessage(err, 'Could not place the order.'))
      setErrors({ ...rest, form: message })
      if (rest.billing_service) { // deactivated meanwhile: offer the current list
        setValues((prev) => ({ ...prev, billing_service: '' }))
        reloadServices()
      }
      setSaving(false)
    }
  }

  return (
    <Panel title="Imaging request" subtitle="You are recorded as the ordering doctor.">
      <form onSubmit={submit} noValidate className="form-stack">
        {errors.form && <Alert variant="error">{errors.form}</Alert>}
        <SelectField label="Imaging Type" name="billing_service" placeholder={loadingServices ? 'Loading…' : 'Choose'}
          options={imagingServiceOptions(services)} value={values.billing_service} onChange={change}
          disabled={!services.length} error={errors.billing_service} />
        {servicesError && (
          <Alert variant="error">{getErrorMessage(servicesError, 'Could not load the imaging types.')}</Alert>
        )}
        {!loadingServices && !servicesError && !services.length && (
          <Alert variant="error">No imaging types are available at the moment.</Alert>
        )}
        <TextAreaField label="Clinical indication" name="clinical_indication" rows={4} maxLength={MAX_INDICATION}
          value={values.clinical_indication} onChange={change} error={errors.clinical_indication}
          hint="Why the scan is needed and what to look for." />
        {encounterId ? (
          <>
            <p className="muted-text">
              Linked to the visit{linkedVisit ? ` of ${visitLabel(linkedVisit)}` : ` (encounter #${encounterId})`}.
            </p>
            {errors.encounter && <Alert variant="error">{errors.encounter}</Alert>}
          </>
        ) : (
          <SelectField label="Visit (encounter)" name="encounter" optional placeholder="Not linked"
            options={(encounters || []).map((e) => ({ value: String(e.encounter_id), label: visitLabel(e) }))}
            value={values.encounter} onChange={change}
            error={errors.encounter || (encountersError ? 'Could not load encounters.' : '')} />
        )}
        <p className="muted-text">
          The patient chooses a scan slot in the portal, or radiology schedules it. No doctor appointment is needed.
        </p>
        <div className="form-actions">
          <Button as={Link} variant="secondary" to={cancelTo}>Cancel</Button>
          <Button type="submit" loading={saving} disabled={!services.length}>Place order</Button>
        </div>
      </form>
    </Panel>
  )
}

/** /imaging/orders/new?patient=&encounter=&from=patient (imaging.order). */
export default function ImagingOrderCreatePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const patientId = searchParams.get('patient')
  const origin = orderOrigin(searchParams)
  const loader = useCallback(() => (patientId ? getPatient(patientId) : Promise.resolve(null)), [patientId])
  const { data: patient, error, loading } = useApi(loader)

  return (
    <>
      <PageHeader back={{ to: origin.to, label: origin.label }} eyebrow="Radiology" title="New imaging order" />
      {!patientId ? <PatientSearch /> : loading ? <LoadingBlock label="Loading patient" /> : error ? (
        <Alert variant="error">{getErrorMessage(error, 'Could not load this patient.')}</Alert>
      ) : patient && (
        <div className="content-stack">
          <div className="patient-summary">
            <span className="patient-summary__mrn">{patientName(patient)}</span>
            <span className="muted-text">· {patient.mrn} · {ageSex(patient)}</span>
            {categoryBadge(patient.category)}
            {!origin.fixed && <Button variant="link" onClick={() => setSearchParams({})}>Change patient</Button>}
          </div>
          <OrderForm key={patient.id} patient={patient} encounterId={searchParams.get('encounter') || ''}
            cancelTo={origin.to} />
        </div>
      )}
    </>
  )
}
