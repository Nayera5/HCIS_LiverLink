import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { listServices } from '../../api/billing'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import { EmptyState, LoadingBlock, Pagination } from '../../components/ui/Feedback'
import { CreditCardIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatMoney, SERVICE_CATEGORY_LABELS, SERVICE_CATEGORY_OPTIONS } from '../Billing/billingDisplay'
import '../Reports/Reports.css' // reuses the tab-button styles
import '../Users/Users.css' // panel-inset

const PAGE_SIZE = 20
const CATEGORY_BUTTONS = [{ value: '', label: 'All' }, ...SERVICE_CATEGORY_OPTIONS]

/**
 * Read-only list of services and prices (services.view: clinical staff and patients).
 * Admins use the full Service catalog page (billing.view) instead. Filters live in the URL.
 */
export default function ServicesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const category = searchParams.get('category') || ''
  const page = Number(searchParams.get('page')) || 1

  const loader = useCallback(
    () => listServices({ category, page, page_size: PAGE_SIZE }),
    [category, page],
  )
  const { data, error, loading } = useApi(loader)

  const update = (changes) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)))
    if (!('page' in changes)) next.delete('page')
    setSearchParams(next)
  }

  return (
    <>
      <PageHeader eyebrow="Billing & payments" title="Services & prices" />

      <div className="report-tabs" role="group" aria-label="Service type">
        {CATEGORY_BUTTONS.map((option) => (
          <button key={option.value || 'all'} type="button" aria-pressed={option.value === category}
            className={`report-tabs__tab ${option.value === category ? 'report-tabs__tab--active' : ''}`}
            onClick={() => update({ category: option.value })}>
            {option.label}
          </button>
        ))}
      </div>

      <Panel title={category ? SERVICE_CATEGORY_LABELS[category] || 'Services' : 'All services'}
        subtitle={data ? `${data.count} service${data.count === 1 ? '' : 's'}` : undefined} flush>
        {error && (
          <div className="panel-inset">
            <Alert variant="error">{getErrorMessage(error, 'Could not load the services.')}</Alert>
          </div>
        )}

        {loading && !data ? (
          <LoadingBlock label="Loading services" />
        ) : data?.results.length ? (
          <>
            <div className="table-wrap" aria-busy={loading}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Code</th>
                    <th scope="col">Name</th>
                    <th scope="col" className="cell-number">Price</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((service) => (
                    <tr key={service.id}>
                      <td><span className="cell-primary">{service.code}</span></td>
                      <td>{service.name}</td>
                      <td className="cell-number">{formatMoney(service.price)}</td>
                      <td>{service.is_active ? <Badge tone="success">Active</Badge> : <Badge>Inactive</Badge>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} count={data.count}
              onPageChange={(next) => update({ page: String(next) })} />
          </>
        ) : (
          !error && (
            <EmptyState icon={CreditCardIcon} title="No services">
              {category ? 'There are no services of this type yet.' : 'No services have been added yet.'}
            </EmptyState>
          )
        )}
      </Panel>
    </>
  )
}
