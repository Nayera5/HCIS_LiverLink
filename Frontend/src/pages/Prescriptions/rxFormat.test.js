import assert from 'node:assert/strict'
import test from 'node:test'
import {
  addDays, changedPlanFields, daysBetween, regimenText, reviewState, todayIso, validatePlan, validatePrescription,
} from './rxFormat.js'

test('addDays and daysBetween handle month and year boundaries', () => {
  assert.equal(addDays('2026-01-30', 3), '2026-02-02')
  assert.equal(addDays('2026-12-31', 1), '2027-01-01')
  assert.equal(addDays('2028-02-28', 1), '2028-02-29')
  assert.equal(daysBetween('2026-01-30', '2026-02-02'), 3)
})

test('todayIso uses local date parts', () => {
  assert.equal(todayIso(new Date(2026, 0, 5, 23, 30)), '2026-01-05')
})

test('validatePrescription mirrors backend rules', () => {
  const ok = { drug: 1, dose: '300 mg', route: 'oral', frequency: 'once daily', start_date: '2026-01-01',
    end_date: '2026-01-31', duration_days: '' }
  assert.deepEqual(validatePrescription(ok), {})
  assert.ok(validatePrescription({ ...ok, end_date: '2026-01-01' }).end_date)
  assert.ok(validatePrescription({ ...ok, end_date: '2025-12-31' }).end_date)
  assert.ok(validatePrescription({ ...ok, duration_days: '0' }).duration_days)
  assert.ok(validatePrescription({ ...ok, duration_days: '2.5' }).duration_days)
  const empty = validatePrescription({ duration_days: '' })
  assert.deepEqual(Object.keys(empty).sort(), ['dose', 'drug', 'frequency', 'route', 'start_date'])
})

test('validatePlan requires a reason only when editing', () => {
  const ok = { plan_type: 'tace', goals: 'Downstage', start_date: '2026-01-01', review_date: '2026-03-01' }
  assert.deepEqual(validatePlan(ok), {})
  assert.ok(validatePlan(ok, { editing: true }).reason)
  assert.deepEqual(validatePlan({ ...ok, reason: 'AFP rise' }, { editing: true }), {})
  assert.ok(validatePlan({ ...ok, review_date: '2025-12-01' }).review_date)
})

test('changedPlanFields sends only real changes and clears review date as null', () => {
  const original = { plan_type: 'tace', goals: 'A', steps: '', start_date: '2026-01-01', review_date: '2026-02-01' }
  assert.deepEqual(changedPlanFields(original, { ...original }), {})
  assert.deepEqual(changedPlanFields(original, { ...original, goals: 'B', review_date: '' }),
    { goals: 'B', review_date: null })
  assert.deepEqual(changedPlanFields({ ...original, steps: null }, { ...original, steps: '' }), {})
})

test('reviewState flags overdue, today and upcoming reviews of active plans only', () => {
  const plan = (review_date, status = 'active') => ({ review_date, status })
  assert.equal(reviewState(plan('2026-01-01'), '2026-01-05'), 'overdue')
  assert.equal(reviewState(plan('2026-01-05'), '2026-01-05'), 'today')
  assert.equal(reviewState(plan('2026-01-10'), '2026-01-05'), 'soon')
  assert.equal(reviewState(plan('2026-03-10'), '2026-01-05'), '')
  assert.equal(reviewState(plan('2026-01-01', 'completed'), '2026-01-05'), '')
  assert.equal(reviewState(plan(null), '2026-01-05'), '')
})

test('regimenText joins dose, route and frequency', () => {
  assert.equal(regimenText({ dose: '300 mg', route: 'oral', frequency: 'once daily' }), '300 mg · Oral · once daily')
})
