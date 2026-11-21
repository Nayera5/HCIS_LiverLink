// Run with `npm test` (Node's built-in test runner; no extra dependencies).
import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import {
  DECISION_LABELS, STATUS_FILTER_OPTIONS, STATUS_LABELS, STATUS_TONES, applicationPayload, isOpen, normalizeMrn,
  isTerminal, statusLabel, validateApplication, validateDecision,
} from './donorApplicationRules.js'

const VALID = { recipient_mrn: 'LL-000123', relationship: 'daughter' }

describe('validateApplication (donor portal)', () => {
  test('MRN and relationship are enough; no date of birth is asked for', () => {
    assert.deepEqual(validateApplication(VALID), {})
    assert.deepEqual(validateApplication({ ...VALID, date_of_birth: '' }), {})
  })

  test('the recipient MRN is required and must look like an MRN', () => {
    assert.deepEqual(validateApplication({ ...VALID, recipient_mrn: '  ' }),
      { recipient_mrn: "Enter the recipient's MRN." })
    assert.deepEqual(validateApplication({ ...VALID, recipient_mrn: '12345' }),
      { recipient_mrn: 'Enter an MRN like LL-000123.' })
  })

  test('lower case and surrounding spaces are accepted', () => {
    assert.deepEqual(validateApplication({ ...VALID, recipient_mrn: ' ll-000123 ' }), {})
  })

  test('the donor cannot name their own MRN', () => {
    assert.deepEqual(validateApplication({ ...VALID, recipient_mrn: 'll-000009' }, { ownMrn: 'LL-000009' }),
      { recipient_mrn: 'The donor and the recipient must be different people.' })
  })

  test('relationship is required and at most 50 characters', () => {
    assert.match(validateApplication({ ...VALID, relationship: ' ' }).relationship, /relationship/)
    assert.match(validateApplication({ ...VALID, relationship: 'x'.repeat(51) }).relationship, /50/)
  })
})

describe('validateApplication (coordinator on behalf of a donor)', () => {
  test('the donor MRN is also required', () => {
    assert.deepEqual(validateApplication(VALID, { forDonor: true }), { donor_mrn: "Enter the donor's MRN." })
    assert.deepEqual(validateApplication({ ...VALID, donor_mrn: 'LL-000001' }, { forDonor: true }), {})
  })

  test('donor and recipient must differ', () => {
    const errors = validateApplication({ ...VALID, donor_mrn: 'LL-000123' }, { forDonor: true })
    assert.equal(errors.recipient_mrn, 'The donor and the recipient must be different people.')
  })
})

describe('applicationPayload', () => {
  test('normalises MRNs and trims text; donor MRN only for staff', () => {
    const values = { recipient_mrn: ' ll-000123', relationship: ' son ', donor_mrn: 'll-000004 ' }
    assert.deepEqual(applicationPayload(values), { recipient_mrn: 'LL-000123', relationship: 'son' })
    assert.deepEqual(applicationPayload(values, { forDonor: true }),
      { recipient_mrn: 'LL-000123', relationship: 'son', donor_mrn: 'LL-000004' })
  })

  test('normalizeMrn handles empty input', () => {
    assert.equal(normalizeMrn(undefined), '')
  })
})

describe('screening decisions', () => {
  test('rejecting needs a reason, unless one is already saved', () => {
    assert.deepEqual(validateDecision('rejected', ''), { screening_notes: 'Give the reason for rejecting the application.' })
    assert.deepEqual(validateDecision('rejected', 'ABO incompatible'), {})
    assert.deepEqual(validateDecision('rejected', '', 'Earlier note'), {})
  })

  test('other decisions do not need notes', () => {
    assert.deepEqual(validateDecision('screening', ''), {})
    assert.deepEqual(validateDecision('accepted', ''), {})
  })

  test('every decision the backend allows has a button label', () => {
    assert.deepEqual(Object.keys(DECISION_LABELS).sort(), ['accepted', 'rejected', 'screening'])
  })
})

describe('statuses', () => {
  test('every backend status has a label and a badge colour', () => {
    const statuses = ['submitted', 'screening', 'accepted', 'rejected', 'withdrawn']
    assert.deepEqual(Object.keys(STATUS_LABELS), statuses)
    assert.deepEqual(Object.keys(STATUS_TONES), statuses)
    assert.equal(statusLabel('accepted'), 'Accepted')
    assert.equal(statusLabel('unknown'), 'unknown')
  })

  test('open statuses match the backend (accepted can still be withdrawn)', () => {
    assert.deepEqual(['submitted', 'screening', 'accepted', 'rejected', 'withdrawn'].map(isOpen),
      [true, true, true, false, false])
  })

  test('accepted can still be withdrawn; only rejected and withdrawn are terminal', () => {
    assert.equal(isOpen('accepted'), true)
    assert.equal(isTerminal('accepted'), false)
    assert.deepEqual(['submitted', 'screening', 'accepted', 'rejected', 'withdrawn'].map(isTerminal),
      [false, false, false, true, true])
    for (const status of ['submitted', 'screening', 'accepted', 'rejected', 'withdrawn']) {
      assert.notEqual(isOpen(status), isTerminal(status), status)  // every status is exactly one of the two
    }
  })

  test('the status filter offers "open" and every status', () => {
    assert.deepEqual(STATUS_FILTER_OPTIONS.map((o) => o.value),
      ['open', 'submitted', 'screening', 'accepted', 'rejected', 'withdrawn'])
  })
})
