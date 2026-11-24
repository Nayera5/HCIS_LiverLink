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
  lab: 'Lab test',
  ai_analysis: 'AI analysis',
  evaluation_package: 'Evaluation package',
  surgery: 'Surgery',
  medical_procedures: 'Medical Procedures',
  inpatient_services: 'Inpatient Services',
  preventive_care: 'Preventive Care',
}

export const SERVICE_CATEGORY_OPTIONS = Object.entries(SERVICE_CATEGORY_LABELS).map(([value, label]) => ({ value, label }))

export const CODING_SYSTEM_LABELS = {
  snomed_ct: 'SNOMED CT',
  cpt: 'CPT',
  hcpcs: 'HCPCS',
  icd10_pcs: 'ICD-10-PCS',
  loinc: 'LOINC',
}

export const CODING_SYSTEM_OPTIONS =
  Object.entries(CODING_SYSTEM_LABELS).map(([value, label]) => ({ value, label }))

export const SERVICE_STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
]

// Desk payments are cash or card; 'online' payments come from the patient portal (Paymob).
const DESK_METHOD_LABELS = { cash: 'Cash', card: 'Card' }
export const PAYMENT_METHOD_LABELS = { ...DESK_METHOD_LABELS, online: 'Online' }
export const PAYMENT_METHOD_OPTIONS = Object.entries(DESK_METHOD_LABELS).map(([value, label]) => ({ value, label }))

export const PAYMENT_STATUS_LABELS = {
  pending: 'Pending', succeeded: 'Succeeded', failed: 'Failed', refunded: 'Refunded',
}

const PAYMENT_STATUS_TONES = { pending: 'info', succeeded: 'success', failed: 'error', refunded: 'neutral' }

export function paymentStatusBadge(status) {
  return <Badge tone={PAYMENT_STATUS_TONES[status] || 'neutral'}>{PAYMENT_STATUS_LABELS[status] || status}</Badge>
}

/** Banner after returning from Paymob (?payment=…): [variant, message] or null. */
export function paymentResultMessage(result) {
  switch (result) {
    case 'succeeded': return ['success', 'Thank you, your payment was received. Your receipt is ready below.']
    case 'failed': return ['error', 'The payment did not go through. No money was taken; you can try again.']
    case 'pending': return ['info', 'Your payment is being processed. Refresh this page in a minute.']
    case 'unverified':
    case 'unknown': return ['warning', 'We could not confirm your payment. If money was taken, it will appear '
      + 'shortly; otherwise please contact the billing desk.']
    default: return null
  }
}

/** "1,700.00 EGP" */
export function formatMoney(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return `${n.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} EGP`
}
