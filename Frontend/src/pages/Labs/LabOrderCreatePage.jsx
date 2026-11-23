import { useCallback, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import { createLabOrder, listLabTests } from '../../api/labs'
import { getPatient, listPatients } from '../../api/patients'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { SearchIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { ageSex, categoryBadge, patientName } from '../Patients/patientDisplay'
import { PRIORITY_OPTIONS } from './labDisplay'
import { rangeText } from './labFormat'
import './Labs.css'

/** Step 1 when no patient is chosen yet: search the registry and pick one. */
function PatientPicker() {
  const [text, setText] = useState('')
  const [term, setTerm] = useState('')
  const [, setSearchParams] = useSearchParams()
  const loader = useCallback(() => (term ? listPatients({ search: term, page_size: 8 }) : Promise.resolve(null)), [term])
  const { data, error, loading } = useApi(loader)

  return (
    <Panel title="Choose a patient" subtitle="Search by name, MRN, national ID or phone.">
      <form className="form-stack" role="search" onSubmit={(event) => { event.preventDefault(); setTerm(text.trim()) }}>
        <TextField label="Search" name="search" value={text} onChange={(event) => setText(event.target.value)}
          placeholder="Name, MRN, national ID or phone"
          endAdornment={
            <button type="submit" className="field__icon-button" aria-label="Search patients">
              <SearchIcon size={18} />
            </button>
          } />
      </form>
      {error && <Alert variant="error" className="form-alert">{getErrorMessage(error, 'Could not search patients.')}</Alert>}
      {loading && !data ? <LoadingBlock label="Searching" /> : null}
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

function OrderForm({ patient }) {
  const navigate = useNavigate()
  const { data: tests, error: testsError, loading } = useApi(listLabTests)
  const [priority, setPriority] = useState('routine')
  const [selected, setSelected] = useState(() => new Set())
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const toggle = (id) => setSelected((prev) => {
    const next = new Set(prev)
    if (!next.delete(id)) next.add(id)
    return next
  })

  const submit = async (event) => {
    event.preventDefault()
    if (!selected.size) {
      setError('Select at least one test.')
      return
    }
    setError('')
    setSaving(true)
    try {
      const order = await createLabOrder({ patient: patient.id, priority, tests: [...selected] })
      navigate(`/lab/orders/${order.id}`, { state: { flash: 'Lab order placed. Results will appear when the lab reports them.' } })
    } catch (err) {
      const fields = fieldErrors(err)
      setError(fields.tests || fields.patient || fields.form || getErrorMessage(err, 'Could not place the order.'))
      setSaving(false)
    }
  }

  if (loading && !tests) return <LoadingBlock label="Loading tests" />
  if (testsError) return <Alert variant="error">{getErrorMessage(testsError, 'Could not load the test catalog.')}</Alert>

  return (
    <form onSubmit={submit} noValidate className="content-stack">
      {error && <Alert variant="error">{error}</Alert>}
      <Panel title="Tests" subtitle="Tick every test to include in this order.">
        <fieldset className="test-grid">
          <legend className="visually-hidden">Tests</legend>
          {tests.map((test) => (
            <label key={test.id} className={`test-option ${selected.has(test.id) ? 'test-option--on' : ''}`}>
              <input type="checkbox" checked={selected.has(test.id)} onChange={() => toggle(test.id)} />
              <span>
                <span className="cell-primary">{test.name}</span>
                <span className="cell-secondary">
                  {test.unit || 'no unit'} · normal {rangeText(test.normal_min, test.normal_max)}
                </span>
              </span>
            </label>
          ))}
        </fieldset>
      </Panel>
      <Panel title="Priority">
        <SelectField label="Priority" options={PRIORITY_OPTIONS} value={priority}
          onChange={(event) => setPriority(event.target.value)} />
      </Panel>
      <div className="form-actions">
        <Button as={Link} to={`/patients/${patient.id}`} variant="secondary">Cancel</Button>
        <Button type="submit" loading={saving}>
          Place order{selected.size ? ` (${selected.size} test${selected.size === 1 ? '' : 's'})` : ''}
        </Button>
      </div>
    </form>
  )
}

export default function LabOrderCreatePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const patientId = searchParams.get('patient')
  const loader = useCallback(() => (patientId ? getPatient(patientId) : Promise.resolve(null)), [patientId])
  const { data: patient, error, loading } = useApi(loader)

  return (
    <>
      <PageHeader back={{ to: '/lab/orders', label: 'Lab orders' }} eyebrow="Laboratory" title="New lab order" />
      {!patientId ? (
        <PatientPicker />
      ) : loading && !patient ? (
        <LoadingBlock label="Loading patient" />
      ) : error ? (
        <Alert variant="error">{getErrorMessage(error, 'Could not load this patient.')}</Alert>
      ) : patient ? (
        <div className="content-stack">
          <div className="patient-summary">
            <span className="patient-summary__mrn">{patientName(patient)}</span>
            <span className="muted-text">· {patient.mrn} · {ageSex(patient)}</span>
            {categoryBadge(patient.category)}
            <Button variant="link" onClick={() => setSearchParams({})}>Change patient</Button>
          </div>
          <OrderForm patient={patient} />
        </div>
      ) : null}
    </>
  )
}
