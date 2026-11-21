// Display formatting helpers (en-GB style dates, as in the design reference).

const LONG_DATE = new Intl.DateTimeFormat('en-GB', {
  weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
})
const DATE_TIME = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
})
const DATE = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })

/** "Sunday, 22 November 2026" */
export function longDate(date = new Date()) {
  return LONG_DATE.format(date)
}

export function formatDateTime(value) {
  return value ? DATE_TIME.format(new Date(value)) : '—'
}

export function formatDate(value) {
  return value ? DATE.format(new Date(value)) : '—'
}

export function greeting(date = new Date()) {
  const hour = date.getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}
