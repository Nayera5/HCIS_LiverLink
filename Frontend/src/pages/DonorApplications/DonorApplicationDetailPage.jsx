import { useCallback, useId, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { getApplication, setApplicationStatus, withdrawApplication } from '../../api/donorApplications'
import { fieldErrors } from '../../api/http'
import { useAuth } from '../../auth/authContext'
import { JOB_TITLE_LABELS } from '../../auth/roles'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { ConfirmDialog, LoadingBlock } from '../../components/ui/Feedback'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { categoryBadge } from '../Patients/patientDisplay'
import { statusBadge } from './applicationDisplay'
import { DECISION_LABELS, statusLabel, validateDecision } from './donorApplicationRules'
import '../Patients/Patients.css'
import './DonorApplications.css'

const BACK = { to: '/donor-applications', label: 'Donor applications' }
const DECISION_VARIANTS = { screening: 'secondary', accepted: 'primary', rejected: 'danger' }

/** One person (donor or recipient). Links to the profile only for staff who may open it (audited). */
function PersonPanel({ title, person, canOpenProfile }) {
  return (
    <Panel title={title} action={canOpenProfile && <Link to={`/patients/${person.id}`}>Open profile</Link>}>
      <dl className="detail-list">
        <div><dt>Name</dt><dd>{person.name}</dd></div>
        <div><dt>MRN</dt><dd>{person.mrn}</dd></div>
        <div><dt>Category</dt><dd>{categoryBadge(person.category)}</dd></div>
        <div><dt>Blood group</dt><dd>{person.blood_group || '—'}</dd></div>
      </dl>
    </Panel>
  )
}

/** Coordinator decision (donor_applications.screen): next statuses come from the backend. */
function ScreeningPanel({ application, onChanged }) {
  const notesId = useId()
  const [notes, setNotes] = useState(application.screening_notes || '')
  const [pending, setPending] = useState(null)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)

  const choose = (status) => {
    const found = validateDecision(status, notes, application.screening_notes)
    setErrors(found)
    setFormError('')
    if (!Object.keys(found).length) setPending(status)
  }

  const confirm = async () => {
    setBusy(true)
    try {
      const updated = await setApplicationStatus(application.id, { status: pending, screening_notes: notes.trim() })
      onChanged(updated, `Application moved to ${statusLabel(updated.status).toLowerCase()}.`)
    } catch (error) {
      const { form, status, ...rest } = fieldErrors(error)
      setErrors(rest)
      setFormError(form || status || (Object.keys(rest).length ? '' : getErrorMessage(error, 'Could not update the status.')))
    } finally {
      setBusy(false)
      setPending(null)
    }
  }

  return (
    <Panel title="Screening decision" subtitle="Notes are visible to staff only, never to the donor.">
      <div className="form-stack">
        {formError && <Alert variant="error">{formError}</Alert>}
        <div className={`field ${errors.screening_notes ? 'field--invalid' : ''}`}>
          <div className="field__label-row">
            <label className="field__label" htmlFor={notesId}>Screening notes</label>
          </div>
          <textarea id={notesId} className="field__input field__textarea" rows={4} maxLength={4000}
            value={notes} onChange={(event) => setNotes(event.target.value)}
            aria-invalid={errors.screening_notes ? 'true' : undefined}
            aria-describedby={errors.screening_notes ? `${notesId}-error` : undefined} />
          {errors.screening_notes
            ? <p id={`${notesId}-error`} className="field__error">{errors.screening_notes}</p>
            : <p className="field__hint">Required when rejecting.</p>}
        </div>
        <div className="inline-actions">
          {application.next_statuses.map((status) => (
            <Button key={status} variant={DECISION_VARIANTS[status] || 'secondary'} onClick={() => choose(status)}>
              {DECISION_LABELS[status] || statusLabel(status)}
            </Button>
          ))}
        </div>
      </div>
      <ConfirmDialog open={Boolean(pending)} title={`${DECISION_LABELS[pending] || ''} this application?`}
        confirmLabel={DECISION_LABELS[pending] || 'Confirm'} tone={pending === 'rejected' ? 'danger' : 'primary'}
        busy={busy} onConfirm={confirm} onCancel={() => setPending(null)}>
        The application from <strong>{application.donor.name}</strong> will move from{' '}
        <strong>{statusLabel(application.status)}</strong> to <strong>{statusLabel(pending)}</strong>.
        {pending === 'accepted' && ' Accepting approves the donor to proceed to the next evaluation stage; it is not'
          + ' medical clearance or surgery approval, and the donor can still withdraw.'}
        {pending === 'rejected' && ' A rejection is final.'} This change is recorded in the audit log.
      </ConfirmDialog>
    </Panel>
  )
}

export default function DonorApplicationDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const { can } = useAuth()
  const loader = useCallback(() => getApplication(id), [id])
  const { data: app, error, loading, setData } = useApi(loader)
  const [flash, setFlash] = useState(location.state?.flash || '')
  const [withdrawing, setWithdrawing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const [screenKey, setScreenKey] = useState(0)

  if (loading && !app) return <LoadingBlock label="Loading application" />
  if (error && !app) {
    return (
      <>
        <PageHeader back={BACK} title="Donor application" />
        <Alert variant="error">{getErrorMessage(error, 'Could not load this application.')}</Alert>
      </>
    )
  }

  const changed = (updated, message) => {
    setData(updated)
    setFlash(message)
    setActionError('')
    setScreenKey((k) => k + 1)
  }

  const withdraw = async () => {
    setBusy(true)
    try {
      changed(await withdrawApplication(app.id), 'The application was withdrawn on behalf of the donor.')
    } catch (err) {
      setActionError(getErrorMessage(err, 'Could not withdraw the application.'))
    } finally {
      setBusy(false)
      setWithdrawing(false)
    }
  }

  const canOpenProfile = can('patients.view')
  const canScreen = can('donor_applications.screen') && app.next_statuses.length > 0
  const canWithdraw = can('donor_applications.submit_on_behalf') && app.is_open

  return (
    <>
      <PageHeader back={BACK} eyebrow={`Donor application #${app.id}`}
        title={`${app.donor.name} → ${app.recipient.name}`}
        actions={canWithdraw && (
          <Button variant="secondary" onClick={() => { setWithdrawing(true); setFlash('') }}>Record withdrawal</Button>
        )} />
      <div className="patient-summary">
        {statusBadge(app.status)}
        <span className="muted-text">Submitted {formatDateTime(app.submitted_at)}</span>
      </div>

      <div className="content-stack">
        {flash && <Alert variant="success">{flash}</Alert>}
        {actionError && <Alert variant="error">{actionError}</Alert>}

        <div className="content-grid content-grid--even">
          <PersonPanel title="Donor" person={app.donor} canOpenProfile={canOpenProfile} />
          <PersonPanel title="Intended recipient" person={app.recipient} canOpenProfile={canOpenProfile} />
        </div>

        <div className="content-grid content-grid--even">
          <Panel title="Application">
            <dl className="detail-list">
              <div><dt>Relationship</dt><dd>{app.relationship}</dd></div>
              <div><dt>Status</dt><dd>{statusBadge(app.status)}</dd></div>
              <div><dt>Submitted</dt><dd>{formatDateTime(app.submitted_at)}</dd></div>
              <div><dt>Last update</dt><dd>{formatDateTime(app.updated_at)}</dd></div>
              <div>
                <dt>Screened by</dt>
                <dd>
                  {app.screened_by
                    ? `${app.screened_by.name} (${JOB_TITLE_LABELS[app.screened_by.job_title] || app.screened_by.job_title})`
                    : '—'}
                </dd>
              </div>
              <div><dt>Screened at</dt><dd>{formatDateTime(app.screened_at)}</dd></div>
            </dl>
            {!canScreen && app.screening_notes && (
              <div className="screening-notes">
                <p className="field__label">Screening notes</p>
                <p>{app.screening_notes}</p>
              </div>
            )}
          </Panel>

          {canScreen ? (
            <ScreeningPanel key={screenKey} application={app} onChanged={changed} />
          ) : (
            <Panel title="Screening">
              <p className="muted-text">
                {app.next_statuses.length
                  ? 'Waiting for the transplant coordinator to screen this application.'
                  : app.status === 'accepted'
                    ? 'Accepted: the donor may proceed to the next evaluation stage. The application stays open and can still be withdrawn.'
                    : `This application is ${statusLabel(app.status).toLowerCase()}; no further changes are possible.`}
              </p>
            </Panel>
          )}
        </div>
      </div>

      <ConfirmDialog open={withdrawing} title="Record withdrawal?" confirmLabel="Withdraw application" tone="danger"
        busy={busy} onConfirm={withdraw} onCancel={() => setWithdrawing(false)}>
        Use this when <strong>{app.donor.name}</strong> has asked to withdraw. The application will be closed and the
        change is recorded in the audit log.
      </ConfirmDialog>
    </>
  )
}
