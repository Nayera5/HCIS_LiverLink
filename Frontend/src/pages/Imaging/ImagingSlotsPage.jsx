import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import { createScanSlots, deleteScanSlot, listImagingRooms, listScanSlots, publishScanSlot } from '../../api/imaging'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock, Pagination } from '../../components/ui/Feedback'
import { ClockIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { CLINIC_TIME_ZONE, dateKey, formatTimeRange, formatWhen } from '../Appointments/appointmentRules'
import {
  ACTIVE_IMAGING_SERVICES, ALL_IMAGING_SERVICES, imagingServiceOptions, slotState, validateSlots,
} from './imagingRules'
import { useImagingServices } from './useImagingServices'
import '../Users/Users.css'
import '../Appointments/Appointments.css'
import './Imaging.css'

const PAGE_SIZE = 50
const EMPTY = {
  billing_service: '', resource_name: '', date: '', start_time: '09:00', end_time: '13:00', slot_minutes: '30',
}

function AddSlotsForm({ onSaved }) {
  const [values, setValues] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const { services, error: servicesError } = useImagingServices(ACTIVE_IMAGING_SERVICES)
  const { data: rooms, error: roomsError, loading: roomsLoading } = useApi(listImagingRooms)
  const change = (event) => setValues((prev) => ({ ...prev, [event.target.name]: event.target.value }))

  const save = async (isPublished) => {
    const found = validateSlots(values)
    setErrors(found)
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      const { length } = await createScanSlots({
        ...values, slot_minutes: Number(values.slot_minutes), is_published: isPublished,
      })
      setValues((prev) => ({ ...EMPTY, billing_service: prev.billing_service }))
      onSaved(`${length} scan slot${length === 1 ? '' : 's'} ${isPublished ? 'published' : 'saved as draft'}.`)
    } catch (err) {
      const { form, ...rest } = fieldErrors(err)
      setErrors({
        ...rest,
        form: form || (Object.keys(rest).length ? '' : getErrorMessage(err, 'Could not add scan slots.')),
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Panel title="Add scan slots" subtitle="The hours are split into equal slots.">
      <form className="form-stack" noValidate onSubmit={(event) => { event.preventDefault(); save(true) }}>
        {errors.form && <Alert variant="error">{errors.form}</Alert>}
        {roomsError && <Alert variant="error">{getErrorMessage(roomsError, 'Could not load rooms.')}</Alert>}
        <div className="imaging-slot-form">
          <SelectField label="Imaging Type" name="billing_service" placeholder="Choose"
            options={imagingServiceOptions(services)} value={values.billing_service} onChange={change}
            error={errors.billing_service || (servicesError ? 'Could not load the imaging types.' : '')} />
          <SelectField label="Room" name="resource_name" placeholder={roomsLoading ? 'Loading rooms…' : 'Choose'}
            options={rooms || []} value={values.resource_name} onChange={change}
            error={errors.resource_name} required disabled={roomsLoading || Boolean(roomsError)} />
          <TextField label="Date" name="date" type="date" min={dateKey()} value={values.date} onChange={change}
            error={errors.date} />
          <TextField label="From" name="start_time" type="time" value={values.start_time} onChange={change}
            error={errors.start_time} />
          <TextField label="To" name="end_time" type="time" value={values.end_time} onChange={change}
            error={errors.end_time} />
          <TextField label="Slot (minutes)" name="slot_minutes" type="number" min="5" step="5"
            value={values.slot_minutes} onChange={change} error={errors.slot_minutes} />
        </div>
        <div className="form-actions">
          <Button variant="secondary" disabled={saving} onClick={() => save(false)}>Save as draft</Button>
          <Button type="submit" loading={saving}>Publish slots</Button>
        </div>
      </form>
    </Panel>
  )
}

/** /imaging/slots (imaging.manage): the radiologist publishes and withdraws scan slots. */
export default function ImagingSlotsPage() {
  const [filters, setFilters] = useState({ billing_service: '', date_from: dateKey(), date_to: '', page: 1 })
  const loader = useCallback(() => listScanSlots({ ...filters, page_size: PAGE_SIZE }), [filters])
  const { data, error, loading, reload } = useApi(loader)
  const { services } = useImagingServices(ALL_IMAGING_SERVICES)
  const [flash, setFlash] = useState('')
  const [actionError, setActionError] = useState('')
  const [busy, setBusy] = useState(false)
  const filter = (event) => setFilters((prev) => ({ ...prev, [event.target.name]: event.target.value, page: 1 }))

  const run = async (action, done) => {
    setBusy(true)
    setActionError('')
    setFlash('')
    try {
      await action()
      setFlash(done)
    } catch (err) {
      setActionError(fieldErrors(err).form || getErrorMessage(err, 'Could not change the slot.'))
    } finally {
      setBusy(false)
      reload()
    }
  }

  return (
    <>
      <PageHeader back={{ to: '/imaging/orders', label: 'Imaging orders' }} eyebrow="Radiology" title="Scan slots" />
      <p className="muted-text form-alert">
        Patients with an imaging order of the same type can choose a published free slot. Times are in the clinic
        time zone ({CLINIC_TIME_ZONE}).
      </p>
      <div className="content-stack">
        {flash && <Alert variant="success">{flash}</Alert>}
        {actionError && <Alert variant="error">{actionError}</Alert>}
        <AddSlotsForm onSaved={(message) => { setActionError(''); setFlash(message); reload() }} />
        <Panel flush>
          <div className="filter-bar filter-bar--imaging">
            <SelectField label="Imaging Type" name="billing_service" placeholder="All types"
              options={imagingServiceOptions(services)} value={filters.billing_service} onChange={filter} />
            <TextField label="From" name="date_from" type="date" value={filters.date_from} onChange={filter} />
            <TextField label="To" name="date_to" type="date" value={filters.date_to} onChange={filter} />
          </div>
          {error && (
            <div className="panel-inset">
              <Alert variant="error">{getErrorMessage(error, 'Could not load scan slots.')}</Alert>
            </div>
          )}
          {loading && !data ? <LoadingBlock label="Loading scan slots" /> : data?.results.length ? (
            <>
              <div className="table-wrap" aria-busy={loading}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th scope="col">When</th>
                      <th scope="col">Imaging Type / resource</th>
                      <th scope="col">State</th>
                      <th scope="col">Booking</th>
                      <th scope="col"><span className="visually-hidden">Actions</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.results.map((slot) => {
                      const state = slotState(slot)
                      return (
                        <tr key={slot.slot_id}>
                          <td className="appt-time">
                            {formatWhen(slot.start_time)}<span className="appt-sub">{formatTimeRange(slot)}</span>
                          </td>
                          <td>{slot.billing_service_name}{slot.resource_name && ` · ${slot.resource_name}`}</td>
                          <td><Badge tone={state.tone}>{state.label}</Badge></td>
                          <td>
                            {slot.booking ? (
                              <Link to={`/imaging/orders/${slot.booking.imaging_order}`}>
                                {slot.booking.patient_name} (order #{slot.booking.imaging_order})
                              </Link>
                            ) : '—'}
                          </td>
                          <td className="cell-actions">
                            {!slot.booking && (
                              <div className="appt-actions">
                                <Button size="sm" variant="secondary" disabled={busy}
                                  onClick={() => run(() => publishScanSlot(slot.slot_id, !slot.is_published),
                                    slot.is_published ? 'Slot withdrawn.' : 'Slot published.')}>
                                  {slot.is_published ? 'Withdraw' : 'Publish'}
                                </Button>
                                {!slot.is_published && (
                                  <Button size="sm" variant="secondary" disabled={busy}
                                    onClick={() => run(() => deleteScanSlot(slot.slot_id), 'Slot deleted.')}>
                                    Delete
                                  </Button>
                                )}
                              </div>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              <Pagination page={filters.page} pageSize={PAGE_SIZE} count={data.count}
                onPageChange={(page) => setFilters((prev) => ({ ...prev, page }))} />
            </>
          ) : !error && (
            <EmptyState icon={ClockIcon} title="No scan slots">Add the hours when scans can be booked.</EmptyState>
          )}
        </Panel>
      </div>
    </>
  )
}
