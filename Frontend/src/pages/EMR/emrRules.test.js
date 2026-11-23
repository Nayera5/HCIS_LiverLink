// Run with `npm test` (Node's built-in test runner; no extra dependencies).
import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import {
  diagnosisPayload, downloadName, encounterPayload, formatBp, groupHistory, historyPayload, normaliseIcd10,
  validateDiagnosis, validateDocument, validateEncounter, validateHistory, validateVitals, vitalsPayload,
} from './emrRules.js'

describe('encounter', () => {
  test('the chief complaint is required; text is trimmed', () => {
    assert.ok(validateEncounter({ chief_complaint: '  ' }).chief_complaint)
    assert.deepEqual(validateEncounter({ chief_complaint: 'Jaundice' }), {})
    assert.deepEqual(encounterPayload({ chief_complaint: ' Jaundice ', clinical_notes: undefined }),
      { chief_complaint: 'Jaundice', clinical_notes: '' })
  })
})

describe('medical history', () => {
  const TODAY = new Date('2026-06-01T12:00:00Z')

  test('type and description are required; onset date cannot be in the future', () => {
    const errors = validateHistory({ history_type: 'nope', description: '', onset_date: '2026-07-01' }, TODAY)
    assert.deepEqual(Object.keys(errors).sort(), ['description', 'history_type', 'onset_date'])
    assert.deepEqual(validateHistory({ history_type: 'allergy', description: 'Penicillin' }, TODAY), {})
  })

  test('empty onset date is sent as null', () => {
    assert.deepEqual(historyPayload({ history_type: 'allergy', description: ' Penicillin ', onset_date: '' }, 7),
      { patient: 7, history_type: 'allergy', description: 'Penicillin', onset_date: null })
  })

  test('groups follow the fixed order and skip empty types', () => {
    const groups = groupHistory([{ history_type: 'surgery' }, { history_type: 'allergy' }, { history_type: 'allergy' }])
    assert.deepEqual(groups.map((g) => [g.type, g.items.length]), [['surgery', 1], ['allergy', 2]])
  })
})

describe('diagnosis', () => {
  test('ICD-10 codes are normalised and checked', () => {
    assert.equal(normaliseIcd10(' k74.6 '), 'K74.6')
    assert.deepEqual(validateDiagnosis({ icd10_code: 'c22.0', description: 'HCC' }), {})
    assert.ok(validateDiagnosis({ icd10_code: '74.6', description: 'x' }).icd10_code)
    assert.ok(validateDiagnosis({ icd10_code: '', description: '' }).description)
  })

  test('only one primary diagnosis per encounter', () => {
    const errors = validateDiagnosis({ icd10_code: 'K74.6', description: 'Cirrhosis', is_primary: true },
      [{ is_primary: true }])
    assert.ok(errors.is_primary)
  })

  test('payload', () => {
    assert.deepEqual(diagnosisPayload({ icd10_code: 'k74.6', description: ' Cirrhosis ', is_primary: true }, 3),
      { encounter: 3, icd10_code: 'K74.6', description: 'Cirrhosis', is_primary: true })
  })
})

describe('vital signs', () => {
  test('at least one reading; systolic above diastolic; positive numbers', () => {
    assert.ok(validateVitals({}).form)
    assert.ok(validateVitals({ bp_systolic: '80', bp_diastolic: '120' }).bp_systolic)
    assert.ok(validateVitals({ pulse: '-3' }).pulse)
    assert.deepEqual(validateVitals({ bp_systolic: '120', bp_diastolic: '80', weight_kg: '70.5' }), {})
  })

  test('empty readings become null', () => {
    const body = vitalsPayload({ pulse: '72', weight_kg: '' }, 4)
    assert.equal(body.encounter, 4)
    assert.equal(body.pulse, 72)
    assert.equal(body.weight_kg, null)
  })

  test('blood pressure display', () => {
    assert.equal(formatBp({ bp_systolic: 120, bp_diastolic: 80 }), '120/80')
    assert.equal(formatBp({ bp_systolic: null, bp_diastolic: null }), '—')
  })
})

describe('documents', () => {
  const ok = { title: 'Outside CT', document_type: 'external_report' }

  test('file type and size follow the backend limits', () => {
    assert.deepEqual(validateDocument(ok, { name: 'scan.PDF', size: 1000 }), {})
    assert.ok(validateDocument(ok, { name: 'run.exe', size: 10 }).file_path)
    assert.ok(validateDocument(ok, { name: 'big.pdf', size: 21 * 1024 * 1024 }).file_path)
    assert.ok(validateDocument(ok, null).file_path)
    assert.ok(validateDocument({ title: '', document_type: '' }, { name: 'a.pdf', size: 1 }).title)
  })

  test('download name gets an extension from the file type', () => {
    assert.equal(downloadName('Outside CT', 'application/pdf'), 'Outside CT.pdf')
    assert.equal(downloadName('scan.png', 'image/png'), 'scan.png')
    assert.equal(downloadName('a/b', 'image/jpeg'), 'a-b.jpg')
    assert.equal(downloadName('', 'text/plain'), 'document')
  })
})
