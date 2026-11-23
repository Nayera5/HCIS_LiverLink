// EMR panels shared by the staff medical record page and the patient portal.
// `patientId` is given on staff pages; in the portal it is omitted (the backend returns only the
// signed-in patient's released records). `canEdit` = holds emr.write (hepatologist, transplant surgeon).
import { forwardRef, useCallback, useId, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import {
  createEncounter, createHistory, deleteDocument, deleteHistory, downloadDocument, listDocuments, listEncounters,
  listHistory, releaseDocument, uploadDocument,
} from '../../api/emr'
import { fieldErrors } from '../../api/http'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { ConfirmDialog, EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { ClipboardIcon, HeartPulseIcon } from '../../components/ui/icons'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { formatDate, formatDateTime } from '../../utils/format'
import {
  DOCUMENT_TYPE_LABELS, ENCOUNTER_STATUS, HISTORY_TYPE_LABELS, downloadName, encounterPayload, groupHistory,
  historyPayload, toOptions, validateDocument, validateEncounter, validateHistory,
} from './emrRules'
import './EMR.css'

const forPatient = (patientId) => (patientId ? { patient: patientId } : {})

/** Multi-line text input matching TextField. */
export const TextAreaField = forwardRef(function TextAreaField({ label, error, hint, id, rows = 4, ...props }, ref) {
  const autoId = useId()
  const inputId = id || autoId
  return (
    <div className={`field ${error ? 'field--invalid' : ''}`}>
      <div className="field__label-row"><label className="field__label" htmlFor={inputId}>{label}</label></div>
      <textarea ref={ref} id={inputId} rows={rows} className="field__input emr-textarea"
        aria-invalid={error ? 'true' : undefined} {...props} />
      {hint && !error && <p className="field__hint">{hint}</p>}
      {error && <p className="field__error">{error}</p>}
    </div>
  )
})

/** Shared form state: values, change handler, and backend error mapping. */
function useForm(initial) {
  const [values, setValues] = useState(initial)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const change = (event) => setValues((prev) => ({ ...prev, [event.target.name]: event.target.value }))

  /** Runs `send()` after `validate()` passes; maps 400 field errors back onto the form. */
  const submit = async (validate, send, fallback) => {
    const found = validate()
    setErrors(found)
    setFormError(found.form || '')
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      await send()
    } catch (error) {
      const { form, ...rest } = fieldErrors(error)
      setErrors(rest)
      setFormError(form || (Object.keys(rest).length ? '' : getErrorMessage(error, fallback)))
    } finally {
      setSaving(false)
    }
  }

  return { values, setValues, errors, formError, saving, change, submit }
}

/** Saves a Blob through a temporary link (the download endpoint needs the access token). */
async function saveDocument(document) {
  const blob = await downloadDocument(document.document_id)
  const url = URL.createObjectURL(blob)
  const link = window.document.createElement('a')
  link.href = url
  link.download = downloadName(document.title, blob.type)
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

// ------------------------------------------------------------------------- Medical history
function HistoryForm({ patientId, onSaved, onCancel }) {
  const form = useForm({ history_type: 'condition', description: '', onset_date: '' })
  const { values, errors } = form

  const save = (event) => {
    event.preventDefault()
    form.submit(() => validateHistory(values),
      async () => onSaved(await createHistory(historyPayload(values, patientId))),
      'Could not save the history item.')
  }

  return (
    <form onSubmit={save} noValidate className="form-stack emr-form">
      {form.formError && <Alert variant="error">{form.formError}</Alert>}
      <SelectField label="Type" name="history_type" value={values.history_type} onChange={form.change}
        options={toOptions(HISTORY_TYPE_LABELS)} error={errors.history_type} />
      <TextAreaField label="Description" name="description" value={values.description} onChange={form.change}
        rows={3} maxLength={4000} error={errors.description} />
      <TextField label="Onset date (optional)" name="onset_date" type="date" value={values.onset_date}
        onChange={form.change} error={errors.onset_date} />
      <div className="form-actions">
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button type="submit" loading={form.saving}>Add to history</Button>
      </div>
    </form>
  )
}

export function HistoryPanel({ patientId, canEdit = false }) {
  const loader = useCallback(() => listHistory(forPatient(patientId)), [patientId])
  const { data: items, error, loading, setData } = useApi(loader)
  const [adding, setAdding] = useState(false)
  const [removing, setRemoving] = useState(null)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')

  const confirmRemove = async () => {
    setBusy(true)
    setActionError('')
    try {
      await deleteHistory(removing.history_id)
      setData(items.filter((i) => i.history_id !== removing.history_id))
    } catch (err) {
      setActionError(getErrorMessage(err, 'Could not delete the item.'))
    } finally {
      setBusy(false)
      setRemoving(null)
    }
  }

  return (
    <Panel title="Medical history" subtitle="Allergies are shown as a warning when prescribing."
      action={canEdit && items && !adding && (
        <Button size="sm" variant="secondary" onClick={() => setAdding(true)}>Add item</Button>
      )}>
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load the medical history.')}</Alert>}
      {actionError && <Alert variant="error" className="form-alert">{actionError}</Alert>}
      {adding && (
        <HistoryForm patientId={patientId} onCancel={() => setAdding(false)}
          onSaved={(created) => { setData([...items, created]); setAdding(false) }} />
      )}

      {loading && !items ? <LoadingBlock label="Loading medical history" /> : items?.length ? (
        <div className="emr-groups">
          {groupHistory(items).map((group) => (
            <section key={group.type} className={`emr-group ${group.type === 'allergy' ? 'emr-group--allergy' : ''}`}>
              <h3 className="emr-group__title">
                {group.label}
                {group.type === 'allergy' && <Badge tone="danger">Allergy</Badge>}
              </h3>
              <ul className="emr-list">
                {group.items.map((item) => (
                  <li key={item.history_id} className="emr-list__item">
                    <div>
                      <div className="emr-pre">{item.description}</div>
                      {item.onset_date && <div className="cell-secondary">Since {formatDate(item.onset_date)}</div>}
                    </div>
                    {canEdit && (
                      <Button size="sm" variant="link" onClick={() => setRemoving(item)}>Delete</Button>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      ) : !adding && <p className="muted-text">No medical history recorded.</p>}

      <ConfirmDialog open={Boolean(removing)} title="Delete history item?" confirmLabel="Delete" tone="danger"
        busy={busy} onConfirm={confirmRemove} onCancel={() => setRemoving(null)}>
        This item will be removed from the medical history. The deletion is recorded in the audit log.
      </ConfirmDialog>
    </Panel>
  )
}

// ------------------------------------------------------------------------------ Encounters
function NewEncounterForm({ patientId, onCancel }) {
  const navigate = useNavigate()
  const form = useForm({ chief_complaint: '', clinical_notes: '' })
  const { values, errors } = form

  const save = (event) => {
    event.preventDefault()
    form.submit(() => validateEncounter(values), async () => {
      const created = await createEncounter({ patient: patientId, ...encounterPayload(values) })
      navigate(`/encounters/${created.encounter_id}`, { state: { flash: 'Encounter started.' } })
    }, 'Could not start the encounter.')
  }

  return (
    <form onSubmit={save} noValidate className="form-stack emr-form">
      {form.formError && <Alert variant="error">{form.formError}</Alert>}
      {errors.staff && <Alert variant="error">{errors.staff}</Alert>}
      <TextField label="Chief complaint" name="chief_complaint" value={values.chief_complaint}
        onChange={form.change} error={errors.chief_complaint} hint="Why the patient came today." />
      <TextAreaField label="Clinical notes (optional)" name="clinical_notes" value={values.clinical_notes}
        onChange={form.change} rows={4} />
      <div className="form-actions">
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button type="submit" loading={form.saving}>Start encounter</Button>
      </div>
    </form>
  )
}

/** encounterLink(id) builds the link to one encounter (staff and portal routes differ). */
export function EncountersPanel({ patientId, canCreate = false, encounterLink }) {
  const loader = useCallback(() => listEncounters(forPatient(patientId)), [patientId])
  const { data: encounters, error, loading } = useApi(loader)
  const [adding, setAdding] = useState(false)

  return (
    <Panel title="Encounters" subtitle={patientId ? 'Visits with the treating doctor.' : 'Your completed visits.'}
      flush={Boolean(encounters?.length) && !adding}
      action={canCreate && !adding && (
        <Button size="sm" onClick={() => setAdding(true)}>New encounter</Button>
      )}>
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load encounters.')}</Alert>}
      {adding && <NewEncounterForm patientId={patientId} onCancel={() => setAdding(false)} />}

      {loading && !encounters ? <LoadingBlock label="Loading encounters" /> : encounters?.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Chief complaint</th>
                <th scope="col" className="hide-sm">Doctor</th>
                <th scope="col">Status</th>
                <th scope="col"><span className="visually-hidden">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {encounters.map((enc) => (
                <tr key={enc.encounter_id}>
                  <td>{formatDateTime(enc.encounter_date)}</td>
                  <td className="cell-primary">{enc.chief_complaint || '—'}</td>
                  <td className="hide-sm">{enc.staff_name || '—'}</td>
                  <td><Badge tone={ENCOUNTER_STATUS[enc.status].tone}>{ENCOUNTER_STATUS[enc.status].label}</Badge></td>
                  <td className="cell-actions"><Link to={encounterLink(enc.encounter_id)}>Open</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : !adding && (
        <EmptyState icon={HeartPulseIcon} title="No encounters yet">
          {patientId ? 'Encounters started by a doctor appear here.' : 'Visits appear here once your doctor signs them.'}
        </EmptyState>
      )}
    </Panel>
  )
}

// ------------------------------------------------------------------------------- Documents
function UploadForm({ patientId, onSaved, onCancel }) {
  const form = useForm({ title: '', document_type: 'external_report' })
  const [file, setFile] = useState(null)
  const { values, errors } = form

  const save = (event) => {
    event.preventDefault()
    form.submit(() => validateDocument(values, file), async () => {
      const body = new FormData()
      body.append('patient', patientId)
      body.append('title', values.title.trim())
      body.append('document_type', values.document_type)
      body.append('file_path', file)
      onSaved(await uploadDocument(body))
    }, 'Could not upload the document.')
  }

  return (
    <form onSubmit={save} noValidate className="form-stack emr-form">
      {form.formError && <Alert variant="error">{form.formError}</Alert>}
      <TextField label="Title" name="title" value={values.title} onChange={form.change} maxLength={255}
        error={errors.title} />
      <SelectField label="Document type" name="document_type" value={values.document_type} onChange={form.change}
        options={toOptions(DOCUMENT_TYPE_LABELS)} error={errors.document_type} />
      <TextField label="File" name="file_path" type="file" accept=".pdf,.jpg,.jpeg,.png"
        onChange={(event) => setFile(event.target.files?.[0] || null)} error={errors.file_path}
        hint="PDF, JPG or PNG, up to 20 MB." />
      <Alert variant="info">The document stays hidden from the patient until you release it.</Alert>
      <div className="form-actions">
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button type="submit" loading={form.saving}>Upload</Button>
      </div>
    </form>
  )
}

export function DocumentsPanel({ patientId, canEdit = false }) {
  const loader = useCallback(() => listDocuments(forPatient(patientId)), [patientId])
  const { data: documents, error, loading, setData } = useApi(loader)
  const [adding, setAdding] = useState(false)
  const [removing, setRemoving] = useState(null)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')

  const replace = (updated) => setData(documents.map((d) => (d.document_id === updated.document_id ? updated : d)))

  const run = async (action, fallback) => {
    setActionError('')
    try {
      await action()
    } catch (err) {
      setActionError(getErrorMessage(err, fallback))
    }
  }

  const confirmRemove = async () => {
    setBusy(true)
    await run(async () => {
      await deleteDocument(removing.document_id)
      setData(documents.filter((d) => d.document_id !== removing.document_id))
    }, 'Could not delete the document.')
    setBusy(false)
    setRemoving(null)
  }

  return (
    <Panel title="Documents & reports"
      subtitle={patientId ? 'External reports, signed consent forms and report PDFs.' : 'Documents your team has shared with you.'}
      flush={Boolean(documents?.length) && !adding && !actionError}
      action={canEdit && !adding && (
        <Button size="sm" variant="secondary" onClick={() => setAdding(true)}>Upload document</Button>
      )}>
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load documents.')}</Alert>}
      {actionError && <Alert variant="error" className="form-alert">{actionError}</Alert>}
      {adding && (
        <UploadForm patientId={patientId} onCancel={() => setAdding(false)}
          onSaved={(created) => { setData([created, ...documents]); setAdding(false) }} />
      )}

      {loading && !documents ? <LoadingBlock label="Loading documents" /> : documents?.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Document</th>
                <th scope="col" className="hide-sm">Uploaded</th>
                {canEdit && <th scope="col">Patient can see</th>}
                <th scope="col"><span className="visually-hidden">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.document_id}>
                  <td>
                    <div className="cell-primary">{doc.title}</div>
                    <div className="cell-secondary">{DOCUMENT_TYPE_LABELS[doc.document_type] || doc.document_type}</div>
                  </td>
                  <td className="hide-sm">{formatDate(doc.uploaded_at)}</td>
                  {canEdit && <td>{doc.is_released ? <Badge tone="success">Released</Badge> : <Badge>Hidden</Badge>}</td>}
                  <td className="cell-actions">
                    <div className="emr-actions">
                      <Button size="sm" variant="link"
                        onClick={() => run(() => saveDocument(doc), 'Could not download the file.')}>
                        Download
                      </Button>
                      {canEdit && (
                        <Button size="sm" variant="link"
                          onClick={() => run(async () => replace(await releaseDocument(doc.document_id, !doc.is_released)),
                            'Could not change who can see the document.')}>
                          {doc.is_released ? 'Hide' : 'Release'}
                        </Button>
                      )}
                      {canEdit && <Button size="sm" variant="link" onClick={() => setRemoving(doc)}>Delete</Button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : !adding && (
        <EmptyState icon={ClipboardIcon} title="No documents">
          {patientId ? 'Uploaded reports appear here.' : 'Documents your team releases to you appear here.'}
        </EmptyState>
      )}

      <ConfirmDialog open={Boolean(removing)} title="Delete document?" confirmLabel="Delete" tone="danger" busy={busy}
        onConfirm={confirmRemove} onCancel={() => setRemoving(null)}>
        <strong>{removing?.title}</strong> will be deleted. A document attached to a consent cannot be deleted.
      </ConfirmDialog>
    </Panel>
  )
}
