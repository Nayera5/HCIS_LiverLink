// Pure helpers for lab values and the trend chart (unit-tested in labFormat.test.js).

const toNumber = (value) => {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

/** "3.4000" -> "3.4", "1000.0000" -> "1,000". Empty (pending) -> "—". */
export function formatValue(value) {
  const number = toNumber(value)
  return number === null ? '—' : number.toLocaleString('en-GB', { maximumFractionDigits: 4 })
}

/** "7 – 56", "≤ 10", "≥ 3.5" or "—". */
export function rangeText(min, max) {
  const lo = toNumber(min)
  const hi = toNumber(max)
  if (lo !== null && hi !== null) return `${formatValue(lo)} – ${formatValue(hi)}`
  if (hi !== null) return `≤ ${formatValue(hi)}`
  if (lo !== null) return `≥ ${formatValue(lo)}`
  return '—'
}

/** Clean axis ticks between min and max (about `target` of them). */
export function niceTicks(min, max, target = 4) {
  if (!(max > min)) return [min]
  const rough = (max - min) / target
  const power = 10 ** Math.floor(Math.log10(rough))
  const fraction = rough / power
  const step = (fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10) * power
  const ticks = []
  for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-9; v += step) {
    ticks.push(Number(v.toFixed(10)))
  }
  return ticks
}

/** Y range that holds every value and the normal range, with air; never below 0 for non-negative data. */
export function yDomain(values, normalMin, normalMax) {
  const all = [...values, normalMin, normalMax].map(toNumber).filter((v) => v !== null)
  if (!all.length) return [0, 1]
  let lo = Math.min(...all)
  let hi = Math.max(...all)
  if (lo === hi) {
    lo -= 1
    hi += 1
  }
  const pad = (hi - lo) * 0.12
  const nonNegative = Math.min(...all) >= 0
  lo -= pad
  hi += pad
  if (nonNegative && lo < 0) lo = 0
  return [lo, hi]
}

/** Horizontal position of a date between the first and last point (centred when there is one date). */
export function xPosition(time, first, last, left, right) {
  if (last === first) return (left + right) / 2
  return left + ((time - first) / (last - first)) * (right - left)
}

export const isAbnormal = (flag) => flag === 'low' || flag === 'high' || flag === 'critical'

const SEVERITY = { critical: 2, high: 1, low: 1 }

/**
 * For the patient page: the latest result of each test with the one before it (`previous`),
 * most serious first. `results` is newest first, as the API returns it.
 */
export function latestPerTest(results) {
  const tests = new Map()
  results.forEach((r) => {
    const latest = tests.get(r.test_code)
    if (!latest) tests.set(r.test_code, { ...r, previous: null })
    else if (!latest.previous) latest.previous = r
  })
  return [...tests.values()].sort((a, b) =>
    (SEVERITY[b.flag] || 0) - (SEVERITY[a.flag] || 0) || a.test_name.localeCompare(b.test_name))
}

/** The flag in plain words. A critical flag has no direction, so it comes from the normal range. */
export function plainFlag({ flag, value, normal_min: min, normal_max: max }) {
  if (flag === 'high') return 'Higher than normal'
  if (flag === 'low') return 'Lower than normal'
  if (flag === 'normal') return 'Normal'
  if (flag !== 'critical') return ''
  const number = toNumber(value)
  if (toNumber(max) !== null && number > toNumber(max)) return 'Critical: very high'
  if (toNumber(min) !== null && number < toNumber(min)) return 'Critical: very low'
  return 'Critical'
}
