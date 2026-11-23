// Reporting & Analytics: tab list, chart data and small formatters (no React, so it can be unit-tested).
// The report shape is documented in Backend/apps/reporting/reports.py.

/**
 * Report tabs. `available: false` tabs are UI placeholders: their backend modules (radiology,
 * AI analysis, transplant) are not built yet, so `planned` lists what the tab will show.
 */
export const REPORT_TABS = [
  { key: 'patients', label: 'Patients & donors', capability: 'reports.patients', available: true },
  { key: 'financial', label: 'Financial', capability: 'reports.financial', available: true },
  { key: 'system_usage', label: 'System usage', capability: 'reports.system_usage', available: true },
  {
    key: 'transplant', label: 'Transplant', capability: 'reports.transplant', available: false,
    planned: ['Cases by stage', 'Approval rate', 'Time from referral to surgery'],
  },
  {
    key: 'imaging', label: 'Imaging & AI', capability: 'reports.imaging', available: false,
    planned: ['Studies per period', 'AI runs', 'Average AI processing time', '% of AI results edited by radiologists'],
  },
]

export const REPORT_CAPABILITIES = REPORT_TABS.map((tab) => tab.capability)

/** Tabs the user may open, in display order. `can` is the auth helper. */
export function tabsFor(can) {
  return REPORT_TABS.filter((tab) => can(tab.capability))
}

/** The tab to show: the requested one if allowed, otherwise the first allowed tab (or null). */
export function pickTab(tabs, requestedKey) {
  return tabs.find((tab) => tab.key === requestedKey) || tabs[0] || null
}

/** Chart points for a section: label = first column, value = the `chart_column` column. */
export function chartData(section) {
  if (section?.chart_column == null) return []
  return section.rows.map((row) => ({ label: String(row[0]), value: Number(row[section.chart_column]) || 0 }))
}

/** Columns whose header ends with "(EGP)" hold money values. */
export function isMoneyColumn(column) {
  return /\(EGP\)$/.test(column)
}

export function formatNumber(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return n.toLocaleString('en-GB', { maximumFractionDigits: 2, minimumFractionDigits: Number.isInteger(n) ? 0 : 2 })
}

/** One table cell: money columns get two decimals, numbers get thousands separators. */
export function formatCell(column, value) {
  if (value === null || value === undefined || value === '') return '—'
  if (isMoneyColumn(column)) {
    const n = Number(value)
    return Number.isNaN(n) ? String(value) : n.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  return typeof value === 'number' ? formatNumber(value) : String(value)
}

/** Validates the date filter; returns { field: message } (empty when valid). */
export function validatePeriod({ date_from: from, date_to: to }) {
  const errors = {}
  const isDate = (text) => /^\d{4}-\d{2}-\d{2}$/.test(text) && !Number.isNaN(Date.parse(text))
  if (from && !isDate(from)) errors.date_from = 'Enter a valid date.'
  if (to && !isDate(to)) errors.date_to = 'Enter a valid date.'
  if (!errors.date_from && !errors.date_to && from && to && from > to) {
    errors.date_to = 'The end date cannot be before the start date.'
  }
  return errors
}

/** "1 Jan 2026 – 31 Mar 2026", "From 1 Jan 2026", "Until …" or "All time". */
export function periodLabel({ date_from: from, date_to: to } = {}) {
  const format = (text) => new Date(`${text}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
  if (from && to) return `${format(from)} – ${format(to)}`
  if (from) return `From ${format(from)}`
  if (to) return `Until ${format(to)}`
  return 'All time'
}
