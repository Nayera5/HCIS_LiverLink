// Run with `npm test` (Node's built-in test runner; no extra dependencies).
import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import { chartData, formatCell, isMoneyColumn, pickTab, tabsFor, validatePeriod } from './reportDisplay.js'

const canFrom = (caps) => (cap) => caps.includes(cap)

describe('report tabs', () => {
  test('only tabs the user may open, in display order', () => {
    const tabs = tabsFor(canFrom(['reports.imaging', 'reports.patients']))
    assert.deepEqual(tabs.map((tab) => tab.key), ['patients', 'imaging'])
  })

  test('billing admin sees only the financial tab; patients see none', () => {
    assert.deepEqual(tabsFor(canFrom(['reports.financial'])).map((tab) => tab.key), ['financial'])
    assert.deepEqual(tabsFor(canFrom(['self.invoices'])), [])
  })

  test('the requested tab is used only when allowed', () => {
    const tabs = tabsFor(canFrom(['reports.patients', 'reports.financial']))
    assert.equal(pickTab(tabs, 'financial').key, 'financial')
    assert.equal(pickTab(tabs, 'system_usage').key, 'patients')
    assert.equal(pickTab([], 'patients'), null)
  })

  test('transplant and imaging tabs are placeholders', () => {
    const tabs = tabsFor(() => true)
    assert.deepEqual(tabs.filter((tab) => !tab.available).map((tab) => tab.key), ['transplant', 'imaging'])
  })
})

describe('chart data', () => {
  test('label from the first column, value from chart_column', () => {
    const section = { chart_column: 2, rows: [['2026-01', 3, '1500.00'], ['2026-02', 1, '200.50']] }
    assert.deepEqual(chartData(section), [{ label: '2026-01', value: 1500 }, { label: '2026-02', value: 200.5 }])
  })

  test('sections without a chart give no points', () => {
    assert.deepEqual(chartData({ chart_column: null, rows: [['x', 1]] }), [])
  })
})

describe('formatting', () => {
  test('money columns get two decimals and separators', () => {
    assert.ok(isMoneyColumn('Collected (EGP)'))
    assert.equal(formatCell('Collected (EGP)', '1500'), '1,500.00')
    assert.equal(formatCell('Patients', 1200), '1,200')
    assert.equal(formatCell('No-show rate', '25.0%'), '25.0%')
    assert.equal(formatCell('Code', ''), '—')
  })
})

describe('date filter', () => {
  test('empty dates are allowed (all time)', () => {
    assert.deepEqual(validatePeriod({ date_from: '', date_to: '' }), {})
  })

  test('the end date cannot be before the start date', () => {
    assert.ok(validatePeriod({ date_from: '2026-03-01', date_to: '2026-02-01' }).date_to)
    assert.deepEqual(validatePeriod({ date_from: '2026-02-01', date_to: '2026-02-01' }), {})
  })

  test('malformed dates are rejected', () => {
    assert.ok(validatePeriod({ date_from: '01/02/2026' }).date_from)
  })
})
