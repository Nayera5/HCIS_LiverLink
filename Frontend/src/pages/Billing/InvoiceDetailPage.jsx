import { useCallback, useState } from 'react'
import { useLocation, useParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { cancelInvoice, downloadReceipt, getInvoice, recordPayment } from '../../api/billing'
import { fieldErrors } from '../../api/http'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { ConfirmDialog, LoadingBlock } from '../../components/ui/Feedback'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { formatDate, formatDateTime } from '../../utils/format'
import {
  formatMoney, invoiceStatusBadge, PAYMENT_METHOD_LABELS, PAYMENT_METHOD_OPTIONS,
} from './billingDisplay'
import './Billing.css'

const BACK = { to: '/billing/invoices', label: 'Invoices' }

function RecordPaymentPanel({ invoice, onRecorded }) {
  const remaining = Number(invoice.total_amount) - Number(invoice.paid_amount)
  const [amount, setAmount] = useState(remaining > 0 ? remaining.toFixed(2) : '')
  const [method, setMethod] = useState('cash')
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const change = (event) => {
    setAmount(event.target.value)
    if (errors.amount) setErrors((prev) => ({ ...prev, amount: '' }))
  }

  const submit = async (event) => {
    event.preventDefault()
    const found = {}
    if (!(Number(amount) > 0)) found.amount = 'Enter an amount greater than 0.'
    else if (Number(amount) > remaining) found.amount = `Amount cannot exceed the remaining balance of ${formatMoney(remaining)}.`
    setErrors(found)
    setFormError('')
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      const { invoice: updated } = await recordPayment(invoice.id, { amount, method })
      onRecorded(updated, 'Payment recorded.')
    } catch (error) {
      const { form, ...rest } = fieldErrors(error)
      setErrors(rest)
      setFormError(form || (Object.keys(rest).length ? '' : getErrorMessage(error, 'Could not record the payment.')))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Panel title="Record a desk payment" subtitle="Cash or card payments taken at the billing desk.">
      <form onSubmit={submit} noValidate className="form-stack">
        {formError && <Alert variant="error">{formError}</Alert>}
        <div className="form-grid__pair">
          <TextField label="Amount (EGP)" name="amount" type="number" min="0.01" max={remaining.toFixed(2)}
            step="100" value={amount} onChange={change} error={errors.amount}
            hint={`Remaining balance: ${formatMoney(remaining)}`} />
          <SelectField label="Method" name="method" value={method} options={PAYMENT_METHOD_OPTIONS}
            onChange={(event) => setMethod(event.target.value)} />
        </div>
        <div className="form-actions">
          <Button type="submit" loading={saving}>Record payment</Button>
        </div>
      </form>
    </Panel>
  )
}

export default function InvoiceDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const { can } = useAuth()
  const loader = useCallback(() => getInvoice(id), [id])
  const { data: invoice, error, loading, setData } = useApi(loader)
  const [flash, setFlash] = useState(location.state?.flash || '')
  const [actionError, setActionError] = useState('')
  const [cancelling, setCancelling] = useState(false)
  const [busy, setBusy] = useState(false)
  const [downloadingId, setDownloadingId] = useState(null)

  if (loading && !invoice) return <LoadingBlock label="Loading invoice" />
  if (error && !invoice) {
    return (
      <>
        <PageHeader back={BACK} title="Invoice" />
        <Alert variant="error">{getErrorMessage(error, 'Could not load this invoice.')}</Alert>
      </>
    )
  }

  const changed = (updated, message) => {
    setData(updated)
    setFlash(message)
    setActionError('')
  }

  const canRecordPayment = can('billing.record_payment')
    && ['unpaid', 'partially_paid'].includes(invoice.status)
  const canCancel = can('billing.create_invoice') && Number(invoice.paid_amount) === 0
    && !['cancelled'].includes(invoice.status)

  const doCancel = async () => {
    setBusy(true)
    try {
      changed(await cancelInvoice(invoice.id), 'The invoice was cancelled.')
    } catch (err) {
      setActionError(getErrorMessage(err, 'Could not cancel the invoice.'))
    } finally {
      setBusy(false)
      setCancelling(false)
    }
  }

  const download = async (paymentId) => {
    setDownloadingId(paymentId)
    setActionError('')
    try {
      await downloadReceipt(paymentId)
    } catch (err) {
      setActionError(getErrorMessage(err, 'Could not download the receipt.'))
    } finally {
      setDownloadingId(null)
    }
  }

  return (
    <>
      <PageHeader back={BACK} eyebrow={`Invoice ${invoice.invoice_no}`} title={invoice.patient_name}
        actions={canCancel && (
          <Button variant="secondary" onClick={() => { setCancelling(true); setFlash('') }}>Cancel invoice</Button>
        )} />
      <div className="patient-summary">
        <span className="muted-text">{invoice.patient_mrn}</span>
        {invoiceStatusBadge(invoice.status)}
        <span className="muted-text">Issued {formatDate(invoice.issue_date)} · Due {formatDate(invoice.due_date)}</span>
      </div>

      <div className="content-stack">
        {flash && <Alert variant="success">{flash}</Alert>}
        {actionError && <Alert variant="error">{actionError}</Alert>}

        <div className="content-grid content-grid--even">
          <Panel title="Items" flush>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Service</th>
                    <th scope="col">Qty</th>
                    <th scope="col">Unit price</th>
                    <th scope="col">Line total</th>
                  </tr>
                </thead>
                <tbody>
                  {invoice.items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <div className="cell-primary">{item.service_name}</div>
                        <div className="cell-secondary">{item.service_code}</div>
                      </td>
                      <td>{item.quantity}</td>
                      <td>{formatMoney(item.unit_price)}</td>
                      <td>{formatMoney(item.line_total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="invoice-summary panel-inset">
              <div className="invoice-summary__item">
                <span className="invoice-summary__label">Total</span>
                <span className="invoice-summary__value">{formatMoney(invoice.total_amount)}</span>
              </div>
              <div className="invoice-summary__item">
                <span className="invoice-summary__label">Paid</span>
                <span className="invoice-summary__value">{formatMoney(invoice.paid_amount)}</span>
              </div>
              <div className="invoice-summary__item">
                <span className="invoice-summary__label">Issued by</span>
                <span className="invoice-summary__value">{invoice.issued_by_name || '—'}</span>
              </div>
            </div>
          </Panel>

          {canRecordPayment ? (
            <RecordPaymentPanel invoice={invoice} onRecorded={changed} />
          ) : (
            <Panel title="Payments">
              <p className="muted-text">
                {invoice.status === 'paid' ? 'This invoice is fully paid.'
                  : invoice.status === 'cancelled' ? 'This invoice is cancelled.'
                    : 'You do not have permission to record payments.'}
              </p>
            </Panel>
          )}
        </div>

        <Panel title="Payment history" flush>
          {invoice.payments.length ? (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Receipt</th>
                    <th scope="col">Amount</th>
                    <th scope="col">Method</th>
                    <th scope="col">Status</th>
                    <th scope="col" className="hide-sm">Received by</th>
                    <th scope="col" className="hide-sm">Paid at</th>
                    <th scope="col"><span className="visually-hidden">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {invoice.payments.map((payment) => (
                    <tr key={payment.id}>
                      <td>{payment.receipt_no}</td>
                      <td>{formatMoney(payment.amount)}</td>
                      <td>{PAYMENT_METHOD_LABELS[payment.method] || payment.method}</td>
                      <td>{payment.status === 'refunded' ? 'Refunded' : 'Succeeded'}</td>
                      <td className="hide-sm">{payment.received_by_name || '—'}</td>
                      <td className="hide-sm">{formatDateTime(payment.paid_at)}</td>
                      <td className="cell-actions">
                        <Button variant="link" size="sm" loading={downloadingId === payment.id}
                          onClick={() => download(payment.id)}>
                          Download receipt
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted-text panel-note">No payments recorded yet.</p>
          )}
        </Panel>
      </div>

      <ConfirmDialog open={cancelling} title="Cancel this invoice?" confirmLabel="Cancel invoice" tone="danger"
        busy={busy} onConfirm={doCancel} onCancel={() => setCancelling(false)}>
        Invoice <strong>{invoice.invoice_no}</strong> will be marked cancelled. This cannot be undone.
      </ConfirmDialog>
    </>
  )
}
