// Pieces shared by the imaging pages.
import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { listImagingOrders } from '../../api/imaging'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { PlusIcon, ScanIcon } from '../../components/ui/icons'
import Panel from '../../components/ui/Panel'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { useSlotAvailability } from '../../hooks/useSlotAvailability'
import { formatDateTime } from '../../utils/format'
import { dateKey, formatDayTitle, formatTimeRange, formatWhen, groupByDay } from '../Appointments/appointmentRules'
import { BOOKING_STATE, IMAGING_STATUS, newOrderLink } from './imagingRules'
import '../Appointments/Appointments.css'
import './Imaging.css'

export function ImagingStatusBadge({ status }) {
  const info = IMAGING_STATUS[status] || { label: status, tone: 'neutral' }
  return <Badge tone={info.tone}>{info.label}</Badge>
}

/** "Sat 28 Nov 09:30" plus whether it is confirmed. */
export function BookingText({ order }) {
  if (!order.appointment) {
    return <span className="muted-text">{order.status === 'ordered' ? BOOKING_STATE.none : '—'}</span>
  }
  return (
    <>
      {formatWhen(order.appointment_start)}
      <span className="appt-sub">{BOOKING_STATE[order.booking_state]}</span>
    </>
  )
}

/** Free scan slots, grouped by day. `load(params)` returns them; `value` is the chosen slot_id. */
export function ScanSlotPicker({ load, value, onChange, error }) {
  const [date, setDate] = useState('')
  const loader = useCallback(() => load({ date }), [load, date])
  const { data, error: loadError, loading, hasDataForLoader } = useSlotAvailability(loader)
  const slots = data || []
  const days = [...new Set(slots.map((slot) => dateKey(slot.start_time)))]

  return (
    <div className="form-stack">
      <TextField label="Date" type="date" value={date} min={dateKey()} hint="Leave empty to see all free slots."
        onChange={(event) => { setDate(event.target.value); onChange('') }} />
      {loading && !hasDataForLoader && <LoadingBlock label="Loading scan slots" />}
      {loadError && <Alert variant="error">{getErrorMessage(loadError, 'Could not load scan slots.')}</Alert>}
      {hasDataForLoader && (slots.length ? (
        <div className="imaging-slots">
          {groupByDay(slots, days).map((group) => (
            <section key={group.date}>
              <p className="field__label">{formatDayTitle(group.date)}</p>
              <div className="slot-grid imaging-slot-grid" role="radiogroup" aria-label={formatDayTitle(group.date)}>
                {group.items.map((slot) => (
                  <button key={slot.slot_id} type="button" role="radio" aria-checked={value === slot.slot_id}
                    className={`slot ${value === slot.slot_id ? 'slot--selected' : ''}`}
                    onClick={() => onChange(slot.slot_id)}>
                    {formatTimeRange(slot)}{slot.resource_name ? ` · ${slot.resource_name}` : ''}
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <p className="muted-text">No free scan slots{date ? ' on this day. Try another date.' : ' at the moment.'}</p>
      ))}
      {error && <p className="field__error">{error}</p>}
    </div>
  )
}

/** Imaging orders of one patient, or of one encounter (staff with imaging.view). `canOrder={false}`: list only. */
export function ImagingOrdersPanel({ patientId, encounterId, from, canOrder = true }) {
  const { can } = useAuth()
  const loader = useCallback(
    () => listImagingOrders({ patient: patientId, encounter: encounterId, page_size: 10 }),
    [patientId, encounterId],
  )
  const { data, error, loading } = useApi(loader)
  const newLink = newOrderLink({ patientId, encounterId, from })

  return (
    <Panel title="Imaging orders" flush={Boolean(data?.results.length)}
      subtitle={encounterId ? 'Requested during this visit.' : undefined}
      action={canOrder && can('imaging.order') && (
        <Button as={Link} size="sm" variant="secondary" icon={PlusIcon} to={newLink}>Order imaging</Button>
      )}>
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load imaging orders.')}</Alert>}
      {loading && !data ? <LoadingBlock label="Loading imaging orders" /> : data?.results.length ? (
        <>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Examination</th>
                  <th scope="col">Status</th>
                  <th scope="col" className="hide-sm">Scan appointment</th>
                  <th scope="col" className="hide-sm">Ordered</th>
                  <th scope="col"><span className="visually-hidden">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((order) => (
                  <tr key={order.imaging_order_id}>
                    <td className="cell-primary">{order.billing_service_name}</td>
                    <td><ImagingStatusBadge status={order.status} /></td>
                    <td className="hide-sm"><BookingText order={order} /></td>
                    <td className="hide-sm">{formatDateTime(order.order_date)}</td>
                    <td className="cell-actions"><Link to={`/imaging/orders/${order.imaging_order_id}`}>Open</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.count > data.results.length && (
            <p className="imaging-more">
              <Link to={`/imaging/orders?patient=${patientId}`}>All imaging orders of this patient</Link>
            </p>
          )}
        </>
      ) : !error && (
        <EmptyState icon={ScanIcon} title="No imaging orders">Requested scans appear here.</EmptyState>
      )}
    </Panel>
  )
}
