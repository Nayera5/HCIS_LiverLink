// Run with `npm test` (Node's built-in test runner; no extra dependencies).
import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import {
  CONSENT_TYPE_LABELS, STATUS_LABELS, STATUS_TONES, availableTypes, consentPayload, consentTypeLabel, toIsoDateTime,
  toLocalInput, unavailableReason, validateConsent,
} from './consentRules.js'

const NOW = new Date('2026-06-01T12:00:00')
const DONOR = { category: 'donor', dateOfBirth: '1990-05-01', consents: [], now: NOW }
const VALID = { consent_type: 'donor_surgery', signed_at: '2026-05-20T10:15', witnessed_by: '' }

describe('consent types (surgery consents only in this stage)', () => {
  test('only donor_surgery and transplant_surgery are offered', () => {
    assert.deepEqual(Object.keys(CONSENT_TYPE_LABELS), ['donor_surgery', 'transplant_surgery'])
    assert.equal(consentTypeLabel('ct_contrast'), 'ct_contrast') // deferred: no label yet
  })

  test('the type follows the person\'s category', () => {
    assert.deepEqual(availableTypes('donor'), ['donor_surgery'])
    assert.deepEqual(availableTypes('recipient'), ['transplant_surgery'])
    assert.deepEqual(availableTypes('liver_patient'), [])
  })

  test('an active consent of a type hides that type; a withdrawn one does not', () => {
    assert.deepEqual(availableTypes('donor', [{ consent_type: 'donor_surgery', status: 'signed' }]), [])
    assert.deepEqual(availableTypes('donor', [{ consent_type: 'donor_surgery', status: 'withdrawn' }]), ['donor_surgery'])
  })

  test('explains why nothing can be recorded', () => {
    assert.match(unavailableReason('liver_patient'), /living donors/)
    assert.match(unavailableReason('donor', [{ consent_type: 'donor_surgery', status: 'signed' }]), /already has an active/)
    assert.equal(unavailableReason('donor'), '')
  })
})

describe('validateConsent', () => {
  test('a complete form is valid; the witness is optional', () => {
    assert.deepEqual(validateConsent(VALID, DONOR), {})
  })

  test('type and signing date are required', () => {
    assert.deepEqual(validateConsent({ consent_type: '', signed_at: '' }, DONOR),
      { consent_type: 'Choose the consent type.', signed_at: 'Enter when the form was signed.' })
  })

  test('rejects a type that does not fit the person', () => {
    assert.match(validateConsent({ ...VALID, consent_type: 'transplant_surgery' }, DONOR).consent_type, /cannot be recorded/)
  })

  test('the signing date cannot be in the future or before birth', () => {
    assert.match(validateConsent({ ...VALID, signed_at: '2026-06-02T09:00' }, DONOR).signed_at, /future/)
    assert.match(validateConsent({ ...VALID, signed_at: '1989-01-01T09:00' }, DONOR).signed_at, /date of birth/)
    assert.match(validateConsent({ ...VALID, signed_at: 'not-a-date' }, DONOR).signed_at, /valid date/)
  })
})

describe('payload and dates', () => {
  test('sends ISO time and a numeric witness or null', () => {
    const body = consentPayload({ ...VALID, witnessed_by: '7' })
    assert.equal(body.consent_type, 'donor_surgery')
    assert.equal(body.witnessed_by, 7)
    assert.equal(body.signed_at, new Date('2026-05-20T10:15').toISOString())
    assert.equal(consentPayload(VALID).witnessed_by, null)
  })

  test('local input round-trips', () => {
    const date = new Date(2026, 4, 20, 10, 5)
    assert.equal(toLocalInput(date), '2026-05-20T10:05')
    assert.equal(toIsoDateTime(''), '')
  })

  test('every status has a label and a colour', () => {
    assert.deepEqual(Object.keys(STATUS_LABELS), ['signed', 'withdrawn'])
    assert.deepEqual(Object.keys(STATUS_TONES), ['signed', 'withdrawn'])
  })
})
