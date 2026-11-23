// Pieces shared by the appointment pages: free-slot picker, appointment table with
// the actions the signed-in user may take (see allowedActions in appointmentRules.js).
import { useCallback, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { createEncounter } from '../../api/emr'
import { fieldErrors } from '../../api/http'
import { changeAppointmentStatus, getFreeSlots, rescheduleAppointment } from '../../api/scheduling'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { ConfirmDialog, LoadingBlock } from '../../components/ui/Feedback'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import {
  APPOINTMENT_STATUS, APPOINTMENT_TYPE_LABELS, allowedActions, dateKey, formatTime, formatTimeRange, formatWhen,
} from './appointmentRules'
import './Appointments.css'

export function StatusBadge({ status }) {
  const info = APPOINTMENT_STATUS[status] || { label: status, tone: 'neutral' }
  return <Badge tone={info.tone}>{info.label}</Badge>
}

/** Buttons for each free slot of `staff` on `date`; `value` is the chosen slot's start_time. */
export function SlotPicker({ staff, date, value, onChange, error }) {
  const loader = useCallback(
    () => (staff && date ? getFreeSlots(staff, date) : Promise.resolve(null)),
    [staff, date],
  )
  const { data, error: loadError, loading } = useApi(loader)

  if (!staff || !date) return <p className="muted-text">Choose a doctor and a date to see free times.</p>
  if (loading) return <LoadingBlock label="Loading free times" />
  if (loadError) return <Alert variant="error">{getErrorMessage(loadError, 'Could not load free times.')}</Alert>

  const slots = data?.slots || []
  return (
    <div className="field">
      <p className="field__label">Free times</p>
      {slots.length ? (
        <div className="slot-grid" role="radiogroup" aria-label="Free times">
          {slots.map((slot) => (
            <button key={slot.start_time} type="button" role="radio" aria-checked={value === slot.start_time}
              className={`slot ${value === slot.start_time ? 'slot--selected' : ''}`}
              onClick={() => onChange(slot.start_time)}>
              {formatTime(slot.start_time)}
            </button>
          ))}
        </div>
      ) : (
        <p className="muted-text">No free times on this day. Try another date.</p>
      )}
      {error && <p className="field__error">{error}</p>}
    </div>
  )
}

function RescheduleDialog({ appointment, onDone, onCancel }) {
  const [date, setDate] = useState(dateKey(appointment.start_time))
  const [start, setStart] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const save = async () => {
    if (!start) {
      setError('Choose a new time.')
      return
    }
    setBusy(true)
    try {
      onDone(await rescheduleAppointment(appointment.appointment_id, { start_time: start }))
    } catch (err) {
      const found = fieldErrors(err)
      setError(found.start_time || found.form || getErrorMessage(err, 'Could not reschedule.'))
      setBusy(false)
    }
  }

  return (
    <ConfirmDialog open title="Reschedule appointment" confirmLabel="Move appointment" busy={busy}
      onConfirm={save} onCancel={onCancel}>
      <div className="form-stack">
        <p>Now: {formatWhen(appointment.start_time)} with {appointment.staff_name}.</p>
        <TextField label="New date" type="date" value={date} min={dateKey()}
          onChange={(e) => { setDate(e.target.value); setStart('') }} />
        <SlotPicker staff={appointment.staff} date={date} value={start}
          onChange={(value) => { setStart(value); setError('') }} error={error} />
      </div>
    </ConfirmDialog>
  )
}

const CONFIRM = {
  cancel: { title: 'Cancel appointment?', label: 'Cancel appointment', tone: 'danger',
    text: 'The time becomes free for others. The appointment is kept in the history as cancelled.' },
  no_show: { title: 'Mark as no-show?', label: 'Mark no-show', tone: 'danger',
    text: 'Use this when the patient did not come.' },
}

const BUTTON_LABELS = {
  reschedule: 'Reschedule', cancel: 'Cancel', check_in: 'Check in', no_show: 'No-show', complete: 'Complete',
  start_encounter: 'Start encounter', open_encounter: 'Open encounter',
}

/** Action buttons for one appointment. `onChanged(updated)` receives the new appointment. */
export function AppointmentActions({ appointment, who, onChanged }) {
  const navigate = useNavigate()
  const [dialog, setDialog] = useState(null) // 'reschedule' | 'cancel' | 'no_show'
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const actions = allowedActions(appointment, who)

  const run = async (action) => {
    setBusy(true)
    setError('')
    try {
      if (action === 'start_encounter') {
        const encounter = await createEncounter({
          patient: appointment.patient,
          appointment: appointment.appointment_id,
          chief_complaint: appointment.reason || APPOINTMENT_TYPE_LABELS[appointment.appointment_type],
        })
        navigate(`/encounters/${encounter.encounter_id}`)
        return
      }
      onChanged(await changeAppointmentStatus(appointment.appointment_id, action))
      setDialog(null)
    } catch (err) {
      setError(getErrorMessage(err, 'Could not update the appointment.'))
      setDialog(null)
    } finally {
      setBusy(false)
    }
  }

  const click = (action) => {
    if (action === 'open_encounter') navigate(`/encounters/${appointment.encounter}`)
    else if (action === 'reschedule' || CONFIRM[action]) setDialog(action)
    else run(action)
  }

  if (!actions.length) return null
  return (
    <div className="appt-actions">
      {actions.map((action) => (
        <Button key={action} size="sm" disabled={busy}
          variant={action === 'cancel' || action === 'no_show' ? 'secondary' : action === 'complete' ? 'outline' : 'primary'}
          onClick={() => click(action)}>
          {BUTTON_LABELS[action]}
        </Button>
      ))}
      {error && <p className="field__error appt-actions__error">{error}</p>}
      {dialog === 'reschedule' && (
        <RescheduleDialog appointment={appointment} onCancel={() => setDialog(null)}
          onDone={(updated) => { setDialog(null); onChanged(updated) }} />
      )}
      {CONFIRM[dialog] && (
        <ConfirmDialog open title={CONFIRM[dialog].title} confirmLabel={CONFIRM[dialog].label}
          tone={CONFIRM[dialog].tone} busy={busy} onConfirm={() => run(dialog)} onCancel={() => setDialog(null)}>
          {formatWhen(appointment.start_time)} · {appointment.patient_name} with {appointment.staff_name}.
          <br />{CONFIRM[dialog].text}
        </ConfirmDialog>
      )}
    </div>
  )
}

/**
 * Table of appointments. `showDate` adds the date to the time column (portal lists);
 * `patientLink` links the patient name to the profile (staff with patients.view).
 */
export function AppointmentTable({ appointments, who, onChanged, showDate = false, showPatient = true,
  patientLink = false }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">{showDate ? 'When' : 'Time'}</th>
            {showPatient && <th scope="col">Patient</th>}
            <th scope="col" className="hide-sm">Doctor</th>
            <th scope="col" className="hide-sm">Type</th>
            <th scope="col">Status</th>
            <th scope="col"><span className="visually-hidden">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          {appointments.map((a) => (
            <tr key={a.appointment_id}>
              <td className="appt-time">{showDate ? formatWhen(a.start_time) : formatTimeRange(a)}</td>
              {showPatient && (
                <td className="cell-primary">
                  {patientLink ? <Link to={`/patients/${a.patient}`}>{a.patient_name}</Link> : a.patient_name}
                  <span className="appt-sub">{a.patient_mrn}</span>
                </td>
              )}
              <td className="hide-sm">{a.staff_name}</td>
              <td className="hide-sm">
                {APPOINTMENT_TYPE_LABELS[a.appointment_type] || a.appointment_type}
                {a.reason && <span className="appt-sub">{a.reason}</span>}
              </td>
              <td><StatusBadge status={a.status} /></td>
              <td className="cell-actions"><AppointmentActions appointment={a} who={who} onChanged={onChanged} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
