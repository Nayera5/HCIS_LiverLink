import { useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { getMyApplications, submitMyApplication, withdrawMyApplication } from '../../api/donorApplications'
import { fieldErrors } from '../../api/http'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { ConfirmDialog, EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { UserPlusIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { formatDate, formatDateTime } from '../../utils/format'
import { statusBadge } from '../DonorApplications/applicationDisplay'
import { applicationPayload, validateApplication } from '../DonorApplications/donorApplicationRules'
import '../Patients/Patients.css'
import '../DonorApplications/DonorApplications.css'

const EMPTY_FORM = { recipient_mrn: '', relationship: '' }

/** New application: the recipient is identified by MRN only (no date of birth or name). */
function ApplicationForm({ onSubmitted }) {
  const [values, setValues] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const change = (event) => setValues((prev) => ({ ...prev, [event.target.name]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    const found = validateApplication(values)
    setErrors(found)
    setFormError('')
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      const created = await submitMyApplication(applicationPayload(values))
      setValues(EMPTY_FORM)
      onSubmitted(created)
    } catch (error) {
      const { form, ...rest } = fieldErrors(error)
      setErrors(rest)
      setFormError(form || (Object.keys(rest).length ? '' : getErrorMessage(error, 'Could not submit your application.')))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate className="form-stack">
      {formError && <Alert variant="error">{formError}</Alert>}
      <TextField label="Recipient's MRN" name="recipient_mrn" placeholder="LL-000123" autoComplete="off"
        maxLength={20} value={values.recipient_mrn} onChange={change} error={errors.recipient_mrn}
        hint="The Medical Record Number of the person you want to donate to. Ask them or their family for it." />
      <TextField label="Your relationship to the recipient" name="relationship" placeholder="e.g. son, wife, brother"
        maxLength={50} value={values.relationship} onChange={change} error={errors.relationship} />
      <div className="form-actions">
        <Button type="submit" loading={saving}>Submit application</Button>
      </div>
    </form>
  )
}

/** Donor portal: own applications only (submit, follow, withdraw). */
export default function MyDonorApplicationsPage() {
  const { data, error, loading, setData } = useApi(getMyApplications)
  const [flash, setFlash] = useState('')
  const [withdrawing, setWithdrawing] = useState(null)
  const [busy, setBusy] = useState(false)
  const [withdrawError, setWithdrawError] = useState('')

  const header = <PageHeader eyebrow="Patient portal" title="My donor applications" />

  if (loading && !data) return <>{header}<LoadingBlock label="Loading your applications" /></>
  if (error && !data) {
    return <>{header}<Alert variant="error">{getErrorMessage(error, 'Could not load your applications.')}</Alert></>
  }

  const replace = (updated) => setData({ ...data, results: data.results.map((a) => (a.id === updated.id ? updated : a)) })

  const confirmWithdraw = async () => {
    setBusy(true)
    setWithdrawError('')
    try {
      replace(await withdrawMyApplication(withdrawing.id))
      setFlash('Your application was withdrawn.')
    } catch (err) {
      setWithdrawError(getErrorMessage(err, 'Could not withdraw the application.'))
    } finally {
      setBusy(false)
      setWithdrawing(null)
    }
  }

  return (
    <>
      {header}
      <div className="content-grid">
        <Panel title="Your applications" subtitle="The transplant coordinator reviews every application.">
          {flash && <Alert variant="success" className="form-alert">{flash}</Alert>}
          {withdrawError && <Alert variant="error" className="form-alert">{withdrawError}</Alert>}
          {data.results.length ? (
            <ul className="application-list">
              {data.results.map((app) => (
                <li key={app.id} className="application-card">
                  <div className="application-card__head">
                    <span className="cell-primary">Recipient {app.recipient_mrn}</span>
                    {statusBadge(app.status)}
                  </div>
                  <dl className="detail-list">
                    <div><dt>Relationship</dt><dd>{app.relationship}</dd></div>
                    <div><dt>Submitted</dt><dd>{formatDate(app.submitted_at)}</dd></div>
                    <div><dt>Last update</dt><dd>{formatDateTime(app.updated_at)}</dd></div>
                  </dl>
                  {app.can_withdraw && (
                    <Button variant="secondary" size="sm" onClick={() => { setWithdrawing(app); setFlash('') }}>
                      Withdraw application
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState icon={UserPlusIcon} title="No applications yet">
              {data.can_apply ? 'Use the form to apply to donate to a registered recipient.' : null}
            </EmptyState>
          )}
        </Panel>

        <Panel title="Apply to donate" subtitle="Identify the intended recipient by their MRN.">
          {data.can_apply ? (
            <ApplicationForm onSubmitted={(created) => {
              setData({ ...data, results: [created, ...data.results] })
              setFlash('Your application was submitted. The transplant coordinator will contact you.')
            }} />
          ) : (
            <Alert variant="info">{data.reason}</Alert>
          )}
        </Panel>
      </div>

      <ConfirmDialog open={Boolean(withdrawing)} title="Withdraw this application?" confirmLabel="Withdraw"
        tone="danger" busy={busy} onConfirm={confirmWithdraw} onCancel={() => setWithdrawing(null)}>
        Your application for recipient <strong>{withdrawing?.recipient_mrn}</strong> will be withdrawn
        {withdrawing?.status === 'accepted' && ', even though it has been accepted for evaluation'}. You can
        apply again later if you change your mind.
      </ConfirmDialog>
    </>
  )
}
