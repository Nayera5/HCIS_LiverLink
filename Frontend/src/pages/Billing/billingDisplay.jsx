// Billing & Payments: labels, badges and small formatters (mirrors apps/billing/models.py).
import Badge from '../../components/ui/Badge'

export const INVOICE_STATUS_LABELS = {
  unpaid: 'Unpaid',
  partially_paid: 'Partially paid',
  paid: 'Paid',
  cancelled: 'Cancelled',
}

const INVOICE_STATUS_TONES = {
  unpaid: 'warning',
  partially_paid: 'info',
  paid: 'success',
  cancelled: 'neutral',
}

export const INVOICE_STATUS_OPTIONS = Object.entries(INVOICE_STATUS_LABELS).map(([value, label]) => ({ value, label }))

export function invoiceStatusBadge(status) {
  return <Badge tone={INVOICE_STATUS_TONES[status] || 'neutral'}>{INVOICE_STATUS_LABELS[status] || status}</Badge>
}

export const SERVICE_CATEGORY_LABELS = {
  consultation: 'Consultation',
  imaging: 'Imaging',
  lab: 'Lab',
  ai_analysis: 'AI analysis',
  evaluation_package: 'Evaluation package',
  surgery: 'Surgery',
}

export const SERVICE_CATEGORY_OPTIONS = Object.entries(SERVICE_CATEGORY_LABELS).map(([value, label]) => ({ value, label }))

export const PAYMENT_METHOD_LABELS = { cash: 'Cash', card: 'Card' }
export const PAYMENT_METHOD_OPTIONS = Object.entries(PAYMENT_METHOD_LABELS).map(([value, label]) => ({ value, label }))

/** "1,700.00 EGP" */
export function formatMoney(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return `${n.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} EGP`
}
