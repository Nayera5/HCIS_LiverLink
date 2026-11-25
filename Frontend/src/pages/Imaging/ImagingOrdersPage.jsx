import { useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { listImagingOrders } from '../../api/imaging'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock, Pagination } from '../../components/ui/Feedback'
import { PlusIcon, ScanIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { BookingText, ImagingStatusBadge } from './imagingParts'
import { ALL_IMAGING_SERVICES, BOOKING_OPTIONS, STATUS_OPTIONS, imagingServiceOptions } from './imagingRules'
import { useImagingServices } from './useImagingServices'
import '../Users/Users.css'
import './Imaging.css'

const PAGE_SIZE = 20
const FILTER_KEYS = ['status', 'booking', 'billing_service', 'patient', 'page']

export default function ImagingOrdersPage() {
  const { can } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = Object.fromEntries(FILTER_KEYS.map((key) => [key, searchParams.get(key) || '']))
  const page = Number(filters.page) || 1

  const query = searchParams.toString()
  const loader = useCallback(
    () => listImagingOrders({ ...Object.fromEntries(new URLSearchParams(query)), page_size: PAGE_SIZE }),
    [query],
  )
  const { data, error, loading } = useApi(loader)
  const { services } = useImagingServices(ALL_IMAGING_SERVICES)

  const update = (changes) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)))
    if (!('page' in changes)) next.delete('page')
    setSearchParams(next)
  }
  const hasFilters = FILTER_KEYS.some((key) => key !== 'page' && filters[key])

  return (
    <>
      <PageHeader eyebrow="Radiology" title="Imaging orders"
        actions={can('imaging.order') && (
          <Button as={Link} icon={PlusIcon}
            to={filters.patient ? `/imaging/orders/new?patient=${filters.patient}` : '/imaging/orders/new'}>
            New imaging order
          </Button>
        )} />
      <Panel flush>
        <div className="filter-bar filter-bar--imaging">
          <SelectField label="Status" placeholder="All statuses" options={STATUS_OPTIONS} value={filters.status}
            onChange={(event) => update({ status: event.target.value })} />
          <SelectField label="Booking" placeholder="All bookings" options={BOOKING_OPTIONS} value={filters.booking}
            onChange={(event) => update({ booking: event.target.value })} />
          <SelectField label="Imaging Type" placeholder="All types" options={imagingServiceOptions(services)}
            value={filters.billing_service} onChange={(event) => update({ billing_service: event.target.value })} />
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
            <Alert variant="error">{getErrorMessage(error, 'Could not load imaging orders.')}</Alert>
          </div>
        )}
        {loading && !data ? <LoadingBlock label="Loading imaging orders" /> : data?.results.length ? (
          <>
            <div className="table-wrap" aria-busy={loading}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Patient</th>
                    <th scope="col">Examination</th>
                    <th scope="col">Status</th>
                    <th scope="col">Scan appointment</th>
                    <th scope="col" className="hide-sm">Ordered by</th>
                    <th scope="col" className="hide-sm">Ordered</th>
                    <th scope="col"><span className="visually-hidden">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((order) => (
                    <tr key={order.imaging_order_id}>
                      <td>
                        <div className="cell-primary">{order.patient_name}</div>
                        <div className="cell-secondary">{order.patient_mrn}</div>
                      </td>
                      <td>{order.billing_service_name}</td>
                      <td><ImagingStatusBadge status={order.status} /></td>
                      <td><BookingText order={order} /></td>
                      <td className="hide-sm">{order.ordered_by_name}</td>
                      <td className="hide-sm">{formatDateTime(order.order_date)}</td>
                      <td className="cell-actions">
                        <Link to={`/imaging/orders/${order.imaging_order_id}`}>Open order</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} count={data.count}
              onPageChange={(next) => update({ page: String(next) })} />
          </>
        ) : !error && (
          <EmptyState icon={ScanIcon} title={hasFilters ? 'No imaging orders match' : 'No imaging orders yet'}>
            {hasFilters ? 'Try other filters.' : 'Imaging orders appear here once a doctor places them.'}
          </EmptyState>
        )}
      </Panel>
    </>
  )
}
