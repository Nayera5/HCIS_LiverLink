// EMR: labels, form checks and request bodies (no React, so `npm test` can import it).
// Mirrors apps/emr (models.py and serializers.py); the backend is the authority.

export const HISTORY_TYPE_LABELS = {
  condition: 'Past conditions',
  liver_etiology: 'Cause of liver disease',
  surgery: 'Previous surgeries',
  allergy: 'Allergies',
  family_history: 'Family history',
}

export const DOCUMENT_TYPE_LABELS = {
  external_report: 'External report',
  consent_form: 'Consent form',
  radiology_report: 'Radiology report',
  lab_report: 'Lab report',
  other: 'Other',
}

export const ENCOUNTER_STATUS = {
  open: { label: 'Open', tone: 'warning' },
  signed: { label: 'Signed', tone: 'success' },
}

export const DIAGNOSIS_STATUS = {
  active: { label: 'Active', tone: 'danger' },
  resolved: { label: 'Resolved', tone: 'neutral' },
}

export const ALLOWED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png']
export const MAX_FILE_SIZE = 20 * 1024 * 1024 // 20 MB, same as the backend

const blank = (value) => value === undefined || value === null || String(value).trim() === ''
const trimmed = (value) => (blank(value) ? '' : String(value).trim())

/** Options for a <SelectField> from a { value: label } map. */
export function toOptions(labels) {
  return Object.entries(labels).map(([value, label]) => ({ value, label }))
}

/** History items grouped by type, in the order of HISTORY_TYPE_LABELS; empty groups are dropped. */
export function groupHistory(items = []) {
  return Object.keys(HISTORY_TYPE_LABELS)
    .map((type) => ({ type, label: HISTORY_TYPE_LABELS[type], items: items.filter((i) => i.history_type === type) }))
    .filter((group) => group.items.length > 0)
}

// --- Encounter ------------------------------------------------------------------
export function validateEncounter(values) {
  const errors = {}
  if (blank(values.chief_complaint)) errors.chief_complaint = 'Enter the reason for the visit.'
  return errors
}

export function encounterPayload(values) {
  return { chief_complaint: trimmed(values.chief_complaint), clinical_notes: trimmed(values.clinical_notes) }
}

// --- Medical history -----------------------------------------------------------
export function validateHistory(values, today = new Date()) {
  const errors = {}
  if (!HISTORY_TYPE_LABELS[values.history_type]) errors.history_type = 'Choose the kind of history item.'
  if (blank(values.description)) errors.description = 'Enter a description.'
  if (values.onset_date && values.onset_date > today.toISOString().slice(0, 10)) {
    errors.onset_date = 'The date cannot be in the future.'
  }
  return errors
}

export function historyPayload(values, patientId) {
  return {
    patient: patientId,
    history_type: values.history_type,
    description: trimmed(values.description),
    onset_date: values.onset_date || null,
  }
}

// --- Diagnosis -------------------------------------------------------------------
/** values: { icd10: { code, description } chosen from the catalog or null, is_primary } */
export function validateDiagnosis(values, diagnoses = []) {
  const errors = {}
  if (!values.icd10) errors.icd10_code = 'Choose a diagnosis from the ICD-10 list.'
  if (values.is_primary && diagnoses.some((d) => d.is_primary)) {
    errors.is_primary = 'This encounter already has a primary diagnosis.'
  }
  return errors
}

export function diagnosisPayload(values, encounterId) {
  return {
    encounter: encounterId,
    icd10_code: values.icd10.code,
    is_primary: Boolean(values.is_primary),
  }
}

// --- Vital signs -----------------------------------------------------------------
export const VITAL_FIELDS = ['bp_systolic', 'bp_diastolic', 'pulse', 'temperature', 'weight_kg', 'height_cm']

export function validateVitals(values) {
  const errors = {}
  const filled = VITAL_FIELDS.filter((f) => !blank(values[f]))
  if (!filled.length) errors.form = 'Enter at least one reading.'
  filled.forEach((field) => {
    const n = Number(values[field])
    if (!Number.isFinite(n) || n <= 0) errors[field] = 'Enter a positive number.'
  })
  const sys = Number(values.bp_systolic)
  const dia = Number(values.bp_diastolic)
  if (!blank(values.bp_systolic) && !blank(values.bp_diastolic) && !errors.bp_systolic && sys <= dia) {
    errors.bp_systolic = 'Systolic must be higher than diastolic.'
  }
  return errors
}

/** Empty readings become null; numbers are sent as numbers. */
export function vitalsPayload(values, encounterId) {
  const body = { encounter: encounterId }
  VITAL_FIELDS.forEach((field) => {
    body[field] = blank(values[field]) ? null : Number(values[field])
  })
  return body
}

/** Blood pressure as "120/80", or '—'. */
export function formatBp(vitals) {
  if (vitals.bp_systolic == null && vitals.bp_diastolic == null) return '—'
  return `${vitals.bp_systolic ?? '—'}/${vitals.bp_diastolic ?? '—'}`
}

// --- Documents -------------------------------------------------------------------
export function fileExtension(name = '') {
  const dot = name.lastIndexOf('.')
  return dot === -1 ? '' : name.slice(dot + 1).toLowerCase()
}

/** file: a File (or { name, size }). */
export function validateDocument(values, file) {
  const errors = {}
  if (blank(values.title)) errors.title = 'Enter a short title.'
  if (!DOCUMENT_TYPE_LABELS[values.document_type]) errors.document_type = 'Choose the document type.'
  if (!file) errors.file_path = 'Choose a file.'
  else if (!ALLOWED_EXTENSIONS.includes(fileExtension(file.name))) errors.file_path = 'Upload a PDF, JPG or PNG file.'
  else if (file.size > MAX_FILE_SIZE) errors.file_path = 'The file is too large (maximum 20 MB).'
  return errors
}

const MIME_EXTENSIONS = { 'application/pdf': 'pdf', 'image/png': 'png', 'image/jpeg': 'jpg' }

/** File name for a downloaded document: its title plus an extension from the file type. */
export function downloadName(title, mimeType) {
  const base = trimmed(title).replace(/[\\/:*?"<>|]+/g, '-') || 'document'
  const ext = MIME_EXTENSIONS[mimeType]
  return ext && fileExtension(base) !== ext ? `${base}.${ext}` : base
}
