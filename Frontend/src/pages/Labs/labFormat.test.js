import assert from 'node:assert/strict'
import test from 'node:test'
import { formatValue, isAbnormal, latestPerTest, niceTicks, plainFlag, rangeText, xPosition, yDomain } from './labFormat.js'

test('formatValue trims zeros and handles pending', () => {
  assert.equal(formatValue('3.4000'), '3.4')
  assert.equal(formatValue('1000.0000'), '1,000')
  assert.equal(formatValue(null), '—')
  assert.equal(formatValue(''), '—')
})

test('rangeText covers both, one-sided and missing ranges', () => {
  assert.equal(rangeText('7.0000', '56.0000'), '7 – 56')
  assert.equal(rangeText(null, '10'), '≤ 10')
  assert.equal(rangeText('3.5', null), '≥ 3.5')
  assert.equal(rangeText(null, null), '—')
})

test('niceTicks returns round, in-range values', () => {
  assert.deepEqual(niceTicks(0, 100), [0, 50, 100])
  assert.deepEqual(niceTicks(0, 3), [0, 1, 2, 3])
  assert.deepEqual(niceTicks(5, 5), [5])
})

test('yDomain includes values and range, and stays non-negative', () => {
  const [lo, hi] = yDomain([0.5, 2.5], '0.1', '1.2')
  assert.equal(lo, 0)
  assert.ok(hi > 2.5)
  const [lo2, hi2] = yDomain([140], '135', '145')
  assert.ok(lo2 < 135 && lo2 >= 0)
  assert.ok(hi2 > 145)
  assert.deepEqual(yDomain([], null, null), [0, 1])
  const [lo3, hi3] = yDomain([4], null, null)
  assert.ok(lo3 < 4 && hi3 > 4)
})

test('xPosition spreads dates and centres a single date', () => {
  assert.equal(xPosition(0, 0, 10, 0, 100), 0)
  assert.equal(xPosition(10, 0, 10, 0, 100), 100)
  assert.equal(xPosition(5, 0, 10, 0, 100), 50)
  assert.equal(xPosition(7, 7, 7, 0, 100), 50)
})

test('isAbnormal', () => {
  assert.equal(isAbnormal('high'), true)
  assert.equal(isAbnormal('normal'), false)
  assert.equal(isAbnormal(''), false)
})

test('latestPerTest keeps the newest result of each test, most serious first', () => {
  const result = (id, code, flag) => ({ id, test_code: code, test_name: code, flag })
  const rows = latestPerTest([
    result(5, 'ALT', 'normal'), result(4, 'INR', 'high'), result(3, 'Bili', 'critical'),
    result(2, 'ALT', 'critical'), result(1, 'ALT', 'high'),
  ])
  assert.deepEqual(rows.map((r) => r.id), [3, 4, 5]) // ALT was critical before, but is normal now
  assert.equal(rows[2].previous.id, 2)
  assert.equal(rows[0].previous, null)
  assert.deepEqual(latestPerTest([]), [])
})

test('plainFlag says the flag in words, with the direction of a critical value', () => {
  const range = { normal_min: '135.0000', normal_max: '145.0000' }
  assert.equal(plainFlag({ ...range, flag: 'critical', value: '165.0000' }), 'Critical: very high')
  assert.equal(plainFlag({ ...range, flag: 'critical', value: '110.0000' }), 'Critical: very low')
  assert.equal(plainFlag({ flag: 'critical', value: '5', normal_min: null, normal_max: null }), 'Critical')
  assert.equal(plainFlag({ ...range, flag: 'high', value: '150' }), 'Higher than normal')
  assert.equal(plainFlag({ ...range, flag: 'low', value: '130' }), 'Lower than normal')
  assert.equal(plainFlag({ ...range, flag: 'normal', value: '140' }), 'Normal')
  assert.equal(plainFlag({ flag: '' }), '')
})
