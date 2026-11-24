import { useCallback, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { downloadMyReceipt, getMyInvoice, payInvoiceOnline } from '../../api/billing'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { LoadingBlock } from '../../components/ui/Feedback'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDate, formatDateTime } from '../../utils/format'
import {
  formatMoney, invoiceStatusBadge, PAYMENT_METHOD_LABELS, paymentResultMessage, paymentStatusBadge,
} from '../Billing/billingDisplay'
import '../Patients/Patients.css'

const BACK = { to: '/my-invoices', label: 'My invoices' }

/**
 * Patient portal: one own invoice, its items and payment history (self.invoices).
 * "Pay online" sends the patient to Paymob's checkout; Paymob sends them back here with
 * ?payment=succeeded|failed|pending (see Backend/apps/billing/paymob.py).
 */
export default function MyInvoiceDetailPage() {
  const { id } = useParams()
  const loader = useCallback(() => getMyInvoice(id), [id])
  const { data: invoice, error, loading } = useApi(loader)
  const [downloadingId, setDownloadingId] = useState(null)
  const [downloadError, setDownloadError] = useState('')
  const [paying, setPaying] = useState(false)
  const [payError, setPayError] = useState('')
  const [searchParams] = useSearchParams()
  const paymentResult = paymentResultMessage(searchParams.get('payment'))

  if (loading && !invoice) return <LoadingBlock label="Loading invoice" />
  if (error && !invoice) {
    return (
      <>
        <PageHeader back={BACK} title="Invoice" />
        <Alert variant="error">{getErrorMessage(error, 'Could not load this invoice.')}</Alert>
      </>
    )
  }

  const download = async (paymentId) => {
    setDownloadingId(paymentId)
    setDownloadError('')
    try {
      await downloadMyReceipt(paymentId)
    } catch (err) {
      setDownloadError(getErrorMessage(err, 'Could not download the receipt.'))
    } finally {
      setDownloadingId(null)
    }
  }

  const balance = Number(invoice.total_amount) - Number(invoice.paid_amount)
  const canPayOnline = invoice.online_payment_available && balance > 0
    && ['unpaid', 'partially_paid'].includes(invoice.status)

  const payOnline = async () => {
    setPaying(true)
    setPayError('')
    try {
      const { checkout_url: checkoutUrl } = await payInvoiceOnline(invoice.id)
      window.location.assign(checkoutUrl)
    } catch (err) {
      setPayError(getErrorMessage(err, 'Could not start the online payment.'))
      setPaying(false)
    }
  }

  return (
    <>
      <PageHeader back={BACK} eyebrow={`Invoice ${invoice.invoice_no}`} title="Invoice details"
        actions={canPayOnline ? (
          <Button loading={paying} onClick={payOnline}>Pay {formatMoney(balance)} online</Button>
        ) : null} />
      <div className="patient-summary">
        {invoiceStatusBadge(invoice.status)}
        <span className="muted-text">Issued {formatDate(invoice.issue_date)} · Due {formatDate(invoice.due_date)}</span>
      </div>

      <div className="content-stack">
        {paymentResult && <Alert variant={paymentResult[0]}>{paymentResult[1]}</Alert>}
        {payError && <Alert variant="error">{payError}</Alert>}
        {downloadError && <Alert variant="error">{downloadError}</Alert>}

        <Panel title="Items" flush>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Service</th>
                  <th scope="col">Qty</th>
                  <th scope="col">Line total</th>
                </tr>
              </thead>
              <tbody>
                {invoice.items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.service_name}</td>
                    <td>{item.quantity}</td>
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
          </div>
        </Panel>

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
                      <td>{paymentStatusBadge(payment.status)}</td>
                      <td className="hide-sm">{formatDateTime(payment.paid_at)}</td>
                      <td className="cell-actions">
                        {payment.has_receipt && (
                          <Button variant="link" size="sm" loading={downloadingId === payment.id}
                            onClick={() => download(payment.id)}>
                            Download receipt
                          </Button>
                        )}
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
    </>
  )
}
