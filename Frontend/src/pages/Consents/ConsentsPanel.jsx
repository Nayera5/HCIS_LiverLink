import { useCallback, useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { listPatientConsents, listWitnesses, recordConsent, withdrawConsent } from '../../api/consents'
import { fieldErrors } from '../../api/http'
import { useAuth } from '../../auth/authContext'
import { JOB_TITLE_LABELS } from '../../auth/roles'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { ConfirmDialog, LoadingBlock } from '../../components/ui/Feedback'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import {
  CONSENT_TYPE_LABELS, STATUS_LABELS, STATUS_TONES, availableTypes, consentPayload, consentTypeLabel, toLocalInput,
  unavailableReason, validateConsent,
} from './consentRules'
import './Consents.css'

const staffName = (staff) => (staff ? `${staff.name} (${JOB_TITLE_LABELS[staff.job_title] || staff.job_title})` : '—')

function RecordConsentForm({ patient, consents, onRecorded, onCancel }) {
  const types = availableTypes(patient.category, consents)
  const { data: witnesses } = useApi(listWitnesses)
  const [values, setValues] = useState({ consent_type: types[0] || '', signed_at: toLocalInput(), witnessed_by: '' })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const change = (event) => setValues((prev) => ({ ...prev, [event.target.name]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    const found = validateConsent(values, { category: patient.category, dateOfBirth: patient.date_of_birth, consents })
    setErrors(found)
    setFormError('')
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      onRecorded(await recordConsent(patient.id, consentPayload(values)))
    } catch (error) {
      const { form, ...rest } = fieldErrors(error)
      setErrors(rest)
      setFormError(form || (Object.keys(rest).length ? '' : getErrorMessage(error, 'Could not record the consent.')))
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate className="form-stack consent-form">
      {formError && <Alert variant="error">{formError}</Alert>}
      <SelectField label="Consent type" name="consent_type" value={values.consent_type} onChange={change}
        options={types.map((value) => ({ value, label: CONSENT_TYPE_LABELS[value] }))} error={errors.consent_type} />
      <TextField label="Signed on" name="signed_at" type="datetime-local" value={values.signed_at} onChange={change}
        max={toLocalInput()} error={errors.signed_at} hint="When the patient signed the paper form." />
      <SelectField label="Witness" name="witnessed_by" value={values.witnessed_by} onChange={change} optional
        placeholder="No witness recorded" error={errors.witnessed_by}
        options={(witnesses || []).map((w) => ({ value: String(w.id), label: staffName(w) }))} />
      <Alert variant="info">
        You are confirming that a signed paper form exists. LiverLink records this; it does not verify the signature.
      </Alert>
      <div className="form-actions">
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button type="submit" loading={saving}>Record signed consent</Button>
      </div>
    </form>
  )
}

/**
 * Consent history on the patient profile. Visible with consents.view (not Super Admin);
 * recording and withdrawing need consents.record. Consents are never deleted.
 */
export default function ConsentsPanel({ patient }) {
  const { can } = useAuth()
  const canRecord = can('consents.record')
  const loader = useCallback(() => listPatientConsents(patient.id), [patient.id])
  const { data: consents, error, loading, setData } = useApi(loader)
  const [adding, setAdding] = useState(false)
  const [flash, setFlash] = useState('')
  const [withdrawing, setWithdrawing] = useState(null)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')

  const confirmWithdraw = async () => {
    setBusy(true)
    setActionError('')
    try {
      const updated = await withdrawConsent(withdrawing.id)
      setData(consents.map((c) => (c.id === updated.id ? updated : c)))
      setFlash(`${consentTypeLabel(updated.consent_type)} consent withdrawn. The record is kept in the history.`)
    } catch (err) {
      setActionError(getErrorMessage(err, 'Could not withdraw the consent.'))
    } finally {
      setBusy(false)
      setWithdrawing(null)
    }
  }

  const reason = consents ? unavailableReason(patient.category, consents) : ''

  return (
    <Panel title="Consents" subtitle="Surgery consents recorded from signed paper forms."
      action={canRecord && consents && !adding && !reason && (
        <Button size="sm" variant="secondary" onClick={() => { setAdding(true); setFlash('') }}>Record consent</Button>
      )}>
      {flash && <Alert variant="success" className="form-alert">{flash}</Alert>}
      {actionError && <Alert variant="error" className="form-alert">{actionError}</Alert>}
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load consents.')}</Alert>}

      {adding && (
        <RecordConsentForm patient={patient} consents={consents} onCancel={() => setAdding(false)}
          onRecorded={(created) => {
            setData([created, ...consents])
            setAdding(false)
            setFlash(`${consentTypeLabel(created.consent_type)} consent recorded.`)
          }} />
      )}

      {loading && !consents ? (
        <LoadingBlock label="Loading consents" />
      ) : consents?.length ? (
        <ul className="consent-list">
          {consents.map((consent) => (
            <li key={consent.id} className={`consent-item ${consent.is_active ? '' : 'consent-item--withdrawn'}`}>
              <div className="consent-item__head">
                <span className="cell-primary">{consent.type_label}</span>
                <Badge tone={STATUS_TONES[consent.status]}>{STATUS_LABELS[consent.status]}</Badge>
              </div>
              <dl className="detail-list">
                <div><dt>Signed on</dt><dd>{formatDateTime(consent.signed_at)}</dd></div>
                <div><dt>Witness</dt><dd>{staffName(consent.witnessed_by)}</dd></div>
                <div><dt>Recorded by</dt><dd>{staffName(consent.recorded_by)}</dd></div>
                {!consent.is_active && (
                  <div>
                    <dt>Withdrawn</dt>
                    <dd>{formatDateTime(consent.withdrawn_at)} by {staffName(consent.withdrawn_by)}</dd>
                  </div>
                )}
              </dl>
              {canRecord && consent.is_active && (
                <Button size="sm" variant="secondary" onClick={() => { setWithdrawing(consent); setFlash('') }}>
                  Record withdrawal
                </Button>
              )}
            </li>
          ))}
        </ul>
      ) : (
        !adding && <p className="muted-text">No consents recorded.</p>
      )}

      {canRecord && reason && consents && !adding && <p className="muted-text panel-note">{reason}</p>}

      <ConfirmDialog open={Boolean(withdrawing)} title="Record consent withdrawal?" confirmLabel="Record withdrawal"
        tone="danger" busy={busy} onConfirm={confirmWithdraw} onCancel={() => setWithdrawing(null)}>
        The <strong>{consentTypeLabel(withdrawing?.consent_type)}</strong> consent of {patient.first_name}{' '}
        {patient.last_name} will be marked as withdrawn. This cannot be undone; the record stays in the history and the
        change is recorded in the audit log.
      </ConfirmDialog>
    </Panel>
  )
}
