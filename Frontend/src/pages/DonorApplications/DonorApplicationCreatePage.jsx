import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { submitApplicationForDonor } from '../../api/donorApplications'
import { fieldErrors } from '../../api/http'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import TextField from '../../components/ui/TextField'
import { applicationPayload, validateApplication } from './donorApplicationRules'
import '../Patients/Patients.css'

/** Coordinator submits on a donor's behalf (donor_applications.submit_on_behalf). Both people by MRN. */
export default function DonorApplicationCreatePage() {
  const navigate = useNavigate()
  const [values, setValues] = useState({ donor_mrn: '', recipient_mrn: '', relationship: '' })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const change = (event) => setValues((prev) => ({ ...prev, [event.target.name]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    const found = validateApplication(values, { forDonor: true })
    setErrors(found)
    setFormError('')
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      const created = await submitApplicationForDonor(applicationPayload(values, { forDonor: true }))
      navigate(`/donor-applications/${created.id}`, { state: { flash: 'Application submitted on behalf of the donor.' } })
    } catch (error) {
      const { form, ...rest } = fieldErrors(error)
      setErrors(rest)
      setFormError(form || (Object.keys(rest).length ? '' : getErrorMessage(error, 'Could not submit the application.')))
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader back={{ to: '/donor-applications', label: 'Donor applications' }} eyebrow="Donor applications"
        title="New application for a donor" />
      <Panel title="Application details"
        subtitle="The donor must be registered as a living donor, and the recipient must have an active case under evaluation.">
        <form onSubmit={submit} noValidate className="form-stack">
          {formError && <Alert variant="error">{formError}</Alert>}
          <TextField label="Donor's MRN" name="donor_mrn" placeholder="LL-000123" autoComplete="off" maxLength={20}
            value={values.donor_mrn} onChange={change} error={errors.donor_mrn} />
          <TextField label="Recipient's MRN" name="recipient_mrn" placeholder="LL-000456" autoComplete="off"
            maxLength={20} value={values.recipient_mrn} onChange={change} error={errors.recipient_mrn}
            hint="Recipient eligibility is checked again when the application is submitted." />
          <TextField label="Relationship to the recipient" name="relationship" placeholder="e.g. son, wife, brother"
            maxLength={50} value={values.relationship} onChange={change} error={errors.relationship} />
          <div className="form-actions">
            <Button variant="secondary" onClick={() => navigate('/donor-applications')}>Cancel</Button>
            <Button type="submit" loading={saving}>Submit application</Button>
          </div>
        </form>
      </Panel>
    </>
  )
}
