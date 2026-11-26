import { useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { listLabOrders } from '../../api/labs'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock, Pagination } from '../../components/ui/Feedback'
import { FlaskIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { PRIORITY_OPTIONS, STATUS_OPTIONS, priorityBadge, statusBadge } from './labDisplay'
import '../Users/Users.css'
import './Labs.css'

const PAGE_SIZE = 20
const FILTER_KEYS = ['status', 'priority', 'patient', 'page']

export default function LabOrdersPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = Object.fromEntries(FILTER_KEYS.map((key) => [key, searchParams.get(key) || '']))
  const page = Number(filters.page) || 1

  const query = searchParams.toString()
  const loader = useCallback(
    () => listLabOrders({ ...Object.fromEntries(new URLSearchParams(query)), page_size: PAGE_SIZE }),
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
      <PageHeader eyebrow="Laboratory" title="Lab orders" />

      <Panel flush>
        <div className="filter-bar filter-bar--labs">
          <SelectField label="Status" placeholder="All statuses" options={STATUS_OPTIONS} value={filters.status}
            onChange={(event) => update({ status: event.target.value })} />
          <SelectField label="Priority" placeholder="Any" options={PRIORITY_OPTIONS} value={filters.priority}
            onChange={(event) => update({ priority: event.target.value })} />
          {hasFilters && (
            <Button variant="link" className="filter-bar__clear" onClick={() => setSearchParams(new URLSearchParams())}>
              Clear filters
            </Button>
          )}
        </div>
        {filters.patient && (
          <p className="panel-inset muted-text">
            Showing orders for one patient. <Link to={`/patients/${filters.patient}`}>Open patient</Link>
          </p>
        )}

        {error && (
          <div className="panel-inset">
            <Alert variant="error">{getErrorMessage(error, 'Could not load lab orders.')}</Alert>
          </div>
        )}

        {loading && !data ? (
          <LoadingBlock label="Loading lab orders" />
        ) : data?.results.length ? (
          <>
            <div className="table-wrap" aria-busy={loading}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Patient</th>
                    <th scope="col">Tests</th>
                    <th scope="col">Priority</th>
                    <th scope="col">Status</th>
                    <th scope="col" className="hide-sm">Ordered</th>
                    <th scope="col"><span className="visually-hidden">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((order) => {
                    const done = order.results.filter((r) => !r.is_pending).length
                    return (
                      <tr key={order.id}>
                        <td>
                          <div className="cell-primary">{order.patient_name}</div>
                          <div className="cell-secondary">{order.patient_mrn}</div>
                        </td>
                        <td>
                          <div>{order.results.map((r) => r.test_name).join(', ')}</div>
                          <div className="cell-secondary">{done} of {order.results.length} resulted</div>
                        </td>
                        <td>{priorityBadge(order.priority)}</td>
                        <td>{statusBadge(order.status)}</td>
                        <td className="hide-sm">{formatDateTime(order.order_date)}</td>
                        <td className="cell-actions"><Link to={`/lab/orders/${order.id}`}>Open order</Link></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} count={data.count}
              onPageChange={(next) => update({ page: String(next) })} />
          </>
        ) : (
          <EmptyState icon={FlaskIcon} title={hasFilters ? 'No lab orders match' : 'No lab orders yet'}>
            {hasFilters ? 'Try other filters.'
              : 'Lab orders appear here once a doctor creates them during an encounter.'}
          </EmptyState>
        )}
      </Panel>
    </>
  )
}
