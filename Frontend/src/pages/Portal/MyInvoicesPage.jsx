import { Link, useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { getMyInvoices } from '../../api/billing'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { ReceiptIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDate } from '../../utils/format'
import Alert from '../../components/ui/Alert'
import { formatMoney, invoiceStatusBadge, paymentResultMessage } from '../Billing/billingDisplay'
import '../Patients/Patients.css'

/** Patient portal: own invoices, balance and payment history (self.invoices). */
export default function MyInvoicesPage() {
  const { data, error, loading } = useApi(getMyInvoices)
  const [searchParams] = useSearchParams()
  const paymentResult = paymentResultMessage(searchParams.get('payment'))

  if (loading && !data) return <LoadingBlock label="Loading your invoices" />
  if (error && !data) {
    return (
      <>
        <PageHeader eyebrow="Patient portal" title="My invoices" />
        <Alert variant="error">{getErrorMessage(error, 'Could not load your invoices.')}</Alert>
      </>
    )
  }

  return (
    <>
      <PageHeader eyebrow="Patient portal" title="My invoices" />
      {paymentResult && <Alert variant={paymentResult[0]} className="form-alert">{paymentResult[1]}</Alert>}
      <div className="patient-summary">
        <span className="muted-text">Outstanding balance</span>
        <strong>{formatMoney(data.outstanding_balance)}</strong>
      </div>

      <Panel flush title="Invoices">
        {data.invoices.length ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Invoice</th>
                  <th scope="col" className="hide-sm">Issued / due</th>
                  <th scope="col">Total</th>
                  <th scope="col" className="hide-sm">Paid</th>
                  <th scope="col">Status</th>
                  <th scope="col"><span className="visually-hidden">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {data.invoices.map((invoice) => (
                  <tr key={invoice.id}>
                    <td><div className="cell-primary">{invoice.invoice_no}</div></td>
                    <td className="hide-sm">{formatDate(invoice.issue_date)} → {formatDate(invoice.due_date)}</td>
                    <td>{formatMoney(invoice.total_amount)}</td>
                    <td className="hide-sm">{formatMoney(invoice.paid_amount)}</td>
                    <td>{invoiceStatusBadge(invoice.status)}</td>
                    <td className="cell-actions">
                      <Link to={`/my-invoices/${invoice.id}`}>Open</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState icon={ReceiptIcon} title="No invoices yet">
            Invoices for your visits and tests will appear here.
          </EmptyState>
        )}
      </Panel>
    </>
  )
}
