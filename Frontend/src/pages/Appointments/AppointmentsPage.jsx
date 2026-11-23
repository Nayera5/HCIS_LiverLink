import { useCallback, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { listAppointments, listDoctors } from '../../api/scheduling'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { LoadingBlock } from '../../components/ui/Feedback'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import { useApi } from '../../hooks/useApi'
import { AppointmentTable } from './appointmentParts'
import './Appointments.css'
import {
  addDays, calendarDays, calendarRange, dateKey, doctorLabel, findMyStaffId, formatDayShort, formatDayTitle, groupByDay,
  replaceRow,
} from './appointmentRules'

/**
 * Staff appointment calendar (appointments.view): day or week view, per doctor or for everyone.
 * `?patient=<id>` shows one patient's calendar (link from the patient profile).
 * Row actions depend on the user: coordinator checks in, the doctor completes, and so on.
 */
export default function AppointmentsPage() {
  const { can } = useAuth()
  const location = useLocation()
  const [params, setParams] = useSearchParams()
  const doctors = useApi(listDoctors).data || []
  const myStaffId = findMyStaffId(doctors)

  const view = params.get('view') === 'week' ? 'week' : 'day'
  const date = params.get('date') || dateKey()
  const patient = params.get('patient') || ''
  // Doctors start on their own calendar; "all" shows every doctor.
  const staffParam = params.get('staff')
  const staff = staffParam === null ? (myStaffId ? String(myStaffId) : '') : staffParam === 'all' ? '' : staffParam

  const update = (changes) => {
    const next = new URLSearchParams(params)
    Object.entries(changes).forEach(([key, value]) => (value === '' ? next.delete(key) : next.set(key, value)))
    setParams(next, { replace: true })
  }

  const loader = useCallback(
    () => listAppointments({ ...calendarRange(view, date), staff, patient }),
    [view, date, staff, patient],
  )
  const { data, error, loading, setData } = useApi(loader)
  const [flash] = useState(location.state?.flash || '')
  const who = { can, myStaffId }
  const days = calendarDays(view, date)
  const groups = groupByDay(data || [], days)
  const step = view === 'week' ? 7 : 1
  const patientName = data?.[0]?.patient_name

  return (
    <>
      <PageHeader eyebrow="Scheduling" title="Appointments"
        actions={can('appointments.book_any') && (
          <Button as={Link} to="/appointments/new" state={patient ? { patientId: patient, patientName } : undefined}>
            Book appointment
          </Button>
        )} />
      {flash && <Alert variant="success" className="form-alert">{flash}</Alert>}
      {patient && (
        <Alert variant="info" className="form-alert">
          Showing the appointments of {patientName || 'the selected patient'}.{' '}
          <Button variant="link" size="sm" onClick={() => update({ patient: '' })}>Show all patients</Button>
        </Alert>
      )}

      <div className="appt-toolbar">
        <div className="segmented" role="group" aria-label="Calendar view">
          {['day', 'week'].map((v) => (
            <button key={v} type="button" className={`segmented__item ${view === v ? 'is-active' : ''}`}
              aria-pressed={view === v} onClick={() => update({ view: v === 'day' ? '' : v })}>
              {v === 'day' ? 'Day' : 'Week'}
            </button>
          ))}
        </div>
        <div className="appt-toolbar__nav">
          <Button variant="secondary" size="sm" onClick={() => update({ date: addDays(date, -step) })}>Previous</Button>
          <Button variant="secondary" size="sm" onClick={() => update({ date: '' })}>Today</Button>
          <Button variant="secondary" size="sm" onClick={() => update({ date: addDays(date, step) })}>Next</Button>
          <input type="date" className="field__input appt-date" aria-label="Go to date" value={date}
            onChange={(e) => update({ date: e.target.value })} />
        </div>
        <SelectField className="appt-toolbar__doctor" aria-label="Doctor" value={staff}
          onChange={(e) => update({ staff: e.target.value || 'all' })}
          placeholder="All doctors" options={doctors.map((d) => ({ value: String(d.staff_id), label: doctorLabel(d) }))} />
      </div>

      <p className="appt-range">
        {view === 'day' ? formatDayTitle(date) : `${formatDayShort(days[0])} – ${formatDayShort(days[6])}`}
      </p>

      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load appointments.')}</Alert>}
      {loading && !data ? <LoadingBlock label="Loading appointments" /> : (
        <div className="content-stack">
          {groups.map((group) => (
            <Panel key={group.date} title={view === 'day' ? 'Schedule' : formatDayTitle(group.date)}
              subtitle={`${group.items.length} appointment${group.items.length === 1 ? '' : 's'}`}
              flush={group.items.length > 0}>
              {group.items.length ? (
                <AppointmentTable appointments={group.items} who={who} patientLink={can('patients.view')}
                  onChanged={(updated) => setData(replaceRow(data, updated))} />
              ) : (
                <p className="muted-text">No appointments.</p>
              )}
            </Panel>
          ))}
        </div>
      )}
    </>
  )
}
