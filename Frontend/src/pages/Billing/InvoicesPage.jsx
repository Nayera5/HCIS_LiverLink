import { useCallback, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { listInvoices } from '../../api/billing'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock, Pagination } from '../../components/ui/Feedback'
import { PlusIcon, ReceiptIcon, SearchIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { formatDate } from '../../utils/format'
import { formatMoney, INVOICE_STATUS_OPTIONS, invoiceStatusBadge } from './billingDisplay'
import '../Users/Users.css'
import './Billing.css'

const PAGE_SIZE = 20
const FILTER_KEYS = ['search', 'status', 'page']

export default function InvoicesPage() {
  const { can } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = Object.fromEntries(FILTER_KEYS.map((key) => [key, searchParams.get(key) || '']))
  const page = Number(filters.page) || 1
  const [searchText, setSearchText] = useState(filters.search)

  const query = searchParams.toString()
  const loader = useCallback(
    () => listInvoices({ ...Object.fromEntries(new URLSearchParams(query)), page_size: PAGE_SIZE }),
    [query],
  )
  const { data, error, loading } = useApi(loader)

  const update = (changes) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)))
    if (!('page' in changes)) next.delete('page')
    setSearchParams(next)
  }
  const hasFilters = FILTER_KEYS.some((key) => key !== 'page' && filters[key])

  return (
    <>
      <PageHeader eyebrow="Billing & payments" title="Invoices"
        actions={can('billing.create_invoice') && (
          <Button as={Link} to="/billing/invoices/new" icon={PlusIcon}>New invoice</Button>
        )} />

      <Panel flush>
        <form className="filter-bar" role="search" onSubmit={(event) => {
          event.preventDefault()
          update({ search: searchText.trim() })
        }}>
          <TextField className="filter-bar__search" label="Search" name="search"
            placeholder="Invoice no., patient name or MRN" value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            endAdornment={
              <button type="submit" className="field__icon-button" aria-label="Search invoices">
                <SearchIcon size={18} />
              </button>
            } />
          <SelectField label="Status" placeholder="Any status" options={INVOICE_STATUS_OPTIONS}
            value={filters.status} onChange={(event) => update({ status: event.target.value })} />
          {hasFilters && (
            <Button variant="link" className="filter-bar__clear" onClick={() => {
              setSearchText('')
              setSearchParams(new URLSearchParams())
            }}>
              Clear filters
            </Button>
          )}
        </form>

        {error && (
          <div className="panel-inset">
            <Alert variant="error">{getErrorMessage(error, 'Could not load invoices.')}</Alert>
          </div>
        )}

        {loading && !data ? (
          <LoadingBlock label="Loading invoices" />
        ) : data?.results.length ? (
          <>
            <div className="table-wrap" aria-busy={loading}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Invoice</th>
                    <th scope="col">Patient</th>
                    <th scope="col" className="hide-sm">Issued / due</th>
                    <th scope="col">Total</th>
                    <th scope="col" className="hide-sm">Paid</th>
                    <th scope="col">Status</th>
                    <th scope="col"><span className="visually-hidden">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((invoice) => (
                    <tr key={invoice.id}>
                      <td><div className="cell-primary">{invoice.invoice_no}</div></td>
                      <td>
                        <div className="cell-primary">{invoice.patient_name}</div>
                        <div className="cell-secondary">{invoice.patient_mrn}</div>
                      </td>
                      <td className="hide-sm">{formatDate(invoice.issue_date)} → {formatDate(invoice.due_date)}</td>
                      <td>{formatMoney(invoice.total_amount)}</td>
                      <td className="hide-sm">{formatMoney(invoice.paid_amount)}</td>
                      <td>{invoiceStatusBadge(invoice.status)}</td>
                      <td className="cell-actions">
                        <Link to={`/billing/invoices/${invoice.id}`}>Open</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} count={data.count}
              onPageChange={(next) => update({ page: String(next) })} />
          </>
        ) : (
          <EmptyState icon={ReceiptIcon} title={hasFilters ? 'No invoices match' : 'No invoices yet'}>
            {hasFilters ? 'Try another search or clear the filters.'
              : can('billing.create_invoice') ? 'Create the first invoice to bill a patient.'
                : 'Invoices appear here once they are created.'}
          </EmptyState>
        )}
      </Panel>
    </>
  )
}
