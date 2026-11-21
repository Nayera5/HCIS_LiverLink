import { useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import { getMyRecord, updateMyContactDetails } from '../../api/patients'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { HeartPulseIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { formatDate } from '../../utils/format'
import { categoryBadge } from '../Patients/patientDisplay'
import '../Patients/Patients.css'

const show = (value, suffix = '') => (value === null || value === undefined || value === '' ? '—' : `${value}${suffix}`)

function ContactForm({ record, onSaved }) {
  const [values, setValues] = useState({
    phone: record.phone || '', address: record.address || '', emergency_contact: record.emergency_contact || '',
  })
  const [errors, setErrors] = useState({})
  const [message, setMessage] = useState(null)
  const [saving, setSaving] = useState(false)

  const change = (event) => {
    setValues((prev) => ({ ...prev, [event.target.name]: event.target.value }))
    setMessage(null)
  }

  const submit = async (event) => {
    event.preventDefault()
    if (!values.phone.trim()) {
      setErrors({ phone: 'Enter a phone number.' })
      return
    }
    setErrors({})
    setSaving(true)
    try {
      const updated = await updateMyContactDetails({
        phone: values.phone.trim(), address: values.address.trim(), emergency_contact: values.emergency_contact.trim(),
      })
      onSaved(updated)
      setMessage({ type: 'success', text: 'Your contact details were saved.' })
    } catch (error) {
      const { form, ...rest } = fieldErrors(error)
      setErrors(rest)
      setMessage({ type: 'error', text: form || getErrorMessage(error, 'Could not save your details.') })
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate className="form-stack">
      {message && <Alert variant={message.type}>{message.text}</Alert>}
      <TextField label="Phone" name="phone" type="tel" maxLength={20} value={values.phone} onChange={change}
        error={errors.phone} autoComplete="tel" />
      <TextField label="Address" name="address" value={values.address} onChange={change} error={errors.address}
        autoComplete="street-address" />
      <TextField label="Emergency contact" name="emergency_contact" maxLength={200} value={values.emergency_contact}
        onChange={change} error={errors.emergency_contact} hint="Name and phone number." />
      <div className="form-actions">
        <Button type="submit" loading={saving}>Save contact details</Button>
      </div>
    </form>
  )
}

/** Patient portal: own record (read-only) + own contact details. */
export default function MyRecordPage() {
  const { data: record, error, loading, setData } = useApi(getMyRecord)

  if (loading && !record) return <LoadingBlock label="Loading your record" />
  if (error && !record) {
    return (
      <>
        <PageHeader eyebrow="Patient portal" title="My health record" />
        <Panel>
          <EmptyState icon={HeartPulseIcon} title="No hospital record yet">
            {error.status === 404 ? error.data?.detail : getErrorMessage(error, 'Could not load your record.')}
          </EmptyState>
        </Panel>
      </>
    )
  }

  return (
    <>
      <PageHeader eyebrow="Patient portal" title="My health record" />
      <div className="patient-summary">
        <span className="patient-summary__mrn">MRN {record.mrn}</span>
        {categoryBadge(record.category)}
      </div>
      <div className="content-grid content-grid--even">
        <div className="content-stack">
          {/* <Panel title="Personal details" subtitle="To correct these details, please contact the hospital.">
            <dl className="detail-list">
              <div><dt>Name</dt><dd>{record.full_name}</dd></div>
              <div><dt>Date of birth</dt><dd>{formatDate(record.date_of_birth)}</dd></div>
              <div><dt>Sex</dt><dd>{record.sex === 'female' ? 'Female' : 'Male'}</dd></div>
              <div><dt>National ID</dt><dd>{show(record.national_id)}</dd></div>
              <div><dt>Blood group</dt><dd>{show(record.blood_group)}</dd></div>
              <div><dt>Height / weight</dt><dd>{show(record.height_cm, ' cm')} · {show(record.weight_kg, ' kg')}</dd></div>
            </dl>
          </Panel> */}
        </div>
        {/* <Panel title="Contact details" subtitle="You can keep these up to date yourself.">
          <ContactForm record={record} onSaved={setData} />
        </Panel> */}
      </div>
    </>
  )
}
