// Run with `npm test` (Node's built-in test runner; no extra dependencies).
import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import {
  ACTION_LABELS, ACTION_OPTIONS, DEFAULT_KIND, KIND_OPTIONS, actionChange, describeRecord, entryKind,
  hasActiveFilters, kindParam, readFilters, toApiParams, validateFilters,
} from './auditLogFilters.js'

const EMPTY = { action: '', kind: '', user: '', patient: '', date_from: '', date_to: '' }
const DEFAULT_VIEW = { ...EMPTY, kind: 'write' }

describe('validateFilters', () => {
  test('empty filters are valid', () => {
    assert.deepEqual(validateFilters(EMPTY), {})
  })

  test('user and patient must be positive numeric IDs', () => {
    assert.deepEqual(validateFilters({ ...EMPTY, user: 'boss', patient: '-3' }),
      { user: 'Enter a numeric ID.', patient: 'Enter a numeric ID.' })
    assert.deepEqual(validateFilters({ ...EMPTY, user: '0' }), { user: 'Enter a numeric ID.' })
    assert.deepEqual(validateFilters({ ...EMPTY, user: ' 12 ', patient: '7' }), {})
  })

  test('dates must be real calendar dates', () => {
    assert.deepEqual(validateFilters({ ...EMPTY, date_from: '2026-02-30' }), { date_from: 'Enter a valid date.' })
    assert.deepEqual(validateFilters({ ...EMPTY, date_to: '03/01/2026' }), { date_to: 'Enter a valid date.' })
  })

  test('end date cannot be before start date; the same day is allowed', () => {
    assert.deepEqual(validateFilters({ ...EMPTY, date_from: '2026-03-05', date_to: '2026-03-01' }),
      { date_to: 'Must be on or after the start date.' })
    assert.deepEqual(validateFilters({ ...EMPTY, date_from: '2026-03-05', date_to: '2026-03-05' }), {})
  })
})

describe('readFilters / toApiParams', () => {
  test('reads every filter from the URL, missing ones as empty and type as the default', () => {
    const filters = readFilters(new URLSearchParams('action=create&user=4&page=2'))
    assert.deepEqual(filters, { ...DEFAULT_VIEW, action: 'create', user: '4' })
  })

  test('sends only valid, non-empty filters', () => {
    assert.deepEqual(toApiParams({
      action: 'category_change', kind: 'write', user: '4', patient: '9',
      date_from: '2026-03-01', date_to: '2026-03-31',
    }), {
      action: 'category_change', kind: 'write', user: '4', patient: '9',
      date_from: '2026-03-01', date_to: '2026-03-31',
    })
    assert.deepEqual(toApiParams(EMPTY), {})
  })

  test('drops hand-edited invalid values instead of sending them', () => {
    assert.deepEqual(toApiParams({
      ...EMPTY, action: 'hack', kind: 'other', user: 'abc', patient: '5', date_from: '2026-13-01',
    }), { patient: '5' })
    // reversed range: the start date is kept, the invalid end date is dropped
    assert.deepEqual(toApiParams({ ...EMPTY, date_from: '2026-03-05', date_to: '2026-03-01' }),
      { date_from: '2026-03-05' })
  })
})

describe('entry display', () => {
  test('profile access is shown as a read, changes as writes', () => {
    assert.deepEqual(entryKind({ action: 'profile_view', is_read: true }), { label: 'Read', tone: 'info' })
    for (const action of ['create', 'update', 'category_change', 'activate', 'deactivate']) {
      assert.equal(entryKind({ action, is_read: false }).label, 'Write', action)
    }
    assert.equal(entryKind({ action: 'login', is_read: false }).label, 'Session')
  })

  test('falls back to the action when the API omits is_read', () => {
    assert.equal(entryKind({ action: 'view' }).label, 'Read')
    assert.equal(entryKind({ action: 'update' }).label, 'Write')
  })

  test('describes the record touched', () => {
    assert.equal(describeRecord({ entity_type: 'registry.patient', entity_id: 12 }), 'Patient record #12')
    assert.equal(describeRecord({ entity_type: 'accounts.user', entity_id: 4 }), 'User account #4')
    assert.equal(describeRecord({ entity_type: 'registry.consent', entity_id: 3 }), 'Consent #3')
    assert.equal(describeRecord({ entity_type: 'labs.result', entity_id: null }), 'labs.result')
  })

  test('the action filter offers every backend action exactly once', () => {
    const offered = ACTION_OPTIONS.flatMap((group) => group.options.map((o) => o.value)).sort()
    assert.deepEqual(offered, Object.keys(ACTION_LABELS).sort())
  })
})

describe('Type filter (defaults to writes)', () => {
  test('offers All, Reads and Writes, and defaults to Writes', () => {
    assert.deepEqual(KIND_OPTIONS.map((o) => [o.value, o.label]), [['all', 'All'], ['read', 'Reads'], ['write', 'Writes']])
    assert.equal(DEFAULT_KIND, 'write')
  })

  test('an empty URL asks the API for writes only', () => {
    const filters = readFilters(new URLSearchParams(''))
    assert.equal(filters.kind, 'write')
    assert.deepEqual(toApiParams(filters), { kind: 'write' })
  })

  test('an unknown type in the URL falls back to writes', () => {
    assert.equal(readFilters(new URLSearchParams('kind=other')).kind, 'write')
  })

  test('All sends no type filter, so profile access is included', () => {
    const filters = readFilters(new URLSearchParams('kind=all'))
    assert.equal(filters.kind, 'all')
    assert.deepEqual(toApiParams(filters), {})
  })

  test('Reads shows profile access', () => {
    assert.deepEqual(toApiParams(readFilters(new URLSearchParams('kind=read&patient=9'))), { kind: 'read', patient: '9' })
  })

  test('the default is kept out of the URL; All and Reads are kept', () => {
    assert.equal(kindParam('write'), '')
    assert.equal(kindParam('all'), 'all')
    assert.equal(kindParam('read'), 'read')
  })

  test('the default view does not count as filtered', () => {
    assert.equal(hasActiveFilters(DEFAULT_VIEW), false)
    assert.equal(hasActiveFilters({ ...DEFAULT_VIEW, kind: 'all' }), true)
    assert.equal(hasActiveFilters({ ...DEFAULT_VIEW, user: '4' }), true)
  })

  test('picking a read action while showing writes widens the type to All', () => {
    assert.deepEqual(actionChange('profile_view', 'write'), { action: 'profile_view', kind: 'all' })
    assert.deepEqual(actionChange('update', 'read'), { action: 'update', kind: 'all' })
  })

  test('picking an action that fits the current type leaves the type alone', () => {
    assert.deepEqual(actionChange('category_change', 'write'), { action: 'category_change' })
    assert.deepEqual(actionChange('profile_view', 'read'), { action: 'profile_view' })
    assert.deepEqual(actionChange('profile_view', 'all'), { action: 'profile_view' })
    assert.deepEqual(actionChange('', 'write'), { action: '' })
  })
})

test('describeChanges lists labelled before/after values', async () => {
  const { describeChanges } = await import('./auditLogFilters.js')
  assert.deepEqual(describeChanges({}), [])
  assert.deepEqual(describeChanges({ changes: { review_date: { from: '2026-01-01', to: null }, is_active: { from: true, to: false } } }), [
    { field: 'Review date', from: '2026-01-01', to: '(empty)' },
    { field: 'Active', from: 'yes', to: 'no' },
  ])
})
