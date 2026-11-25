import { useCallback, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import { listPatients } from '../../api/patients'
import { bookAppointment, listDoctors } from '../../api/scheduling'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { TextAreaField } from '../EMR/emrPanels'
import { DoctorAvailability } from './appointmentParts'
import {
  BOOKABLE_APPOINTMENT_TYPE_LABELS, bookingPayload, dateKey, doctorLabel, formatDayTitle, formatWhen,
  toOptions, validateBooking,
} from './appointmentRules'

/** Staff: search and pick the patient (results come from the patient registry). */
function PatientPicker({ value, onChange, error }) {
  const [search, setSearch] = useState('')
  const loader = useCallback(
    () => (search.trim().length >= 2 ? listPatients({ search: search.trim(), page_size: 8 }) : Promise.resolve(null)),
    [search],
  )
  const { data, loading } = useApi(loader)

  if (value) {
    return (
      <div className="field">
        <p className="field__label">Patient</p>
        <div className="appt-picked">
          <span className="cell-primary">{value.name}</span>
          {value.mrn && <span className="muted-text">{value.mrn}</span>}
          <Button variant="link" size="sm" onClick={() => onChange(null)}>Change</Button>
        </div>
      </div>
    )
  }

  const results = data?.results || []
  return (
    <div className="form-stack">
      <TextField label="Patient" type="search" value={search} onChange={(e) => setSearch(e.target.value)}
        placeholder="Search by name, MRN or national ID" error={error}
        hint="Type at least 2 characters." />
      {loading && search.trim().length >= 2 && <p className="muted-text">Searching…</p>}
      {results.length > 0 && (
        <ul className="appt-results">
          {results.map((p) => (
            <li key={p.id}>
              <button type="button" className="appt-result"
                onClick={() => onChange({ id: p.id, name: `${p.first_name} ${p.last_name}`, mrn: p.mrn })}>
                <span className="cell-primary">{p.first_name} {p.last_name}</span>
                <span className="muted-text">{p.mrn}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {data && !results.length && <p className="muted-text">No patients match.</p>}
    </div>
  )
}

/**
 * Book an appointment. Coordinator / super admin (appointments.book_any) choose the patient;
 * patients and donors (self.appointments) book for themselves. Times come from the doctor's free slots.
 */
export default function BookAppointmentPage() {
  const { can } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const portal = !can('appointments.book_any')
  const needsPatient = !portal
  const { data: doctorRows, error: doctorsError } = useApi(listDoctors)
  const doctors = doctorRows || []

  const preset = location.state?.patientId
    ? { id: Number(location.state.patientId), name: location.state.patientName || 'Selected patient' }
    : null
  const [patient, setPatient] = useState(preset)
  const [values, setValues] = useState({
    staff: '', appointment_type: 'consultation', date: '', start_time: '', reason: '',
  })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const change = (event) => {
    const { name, value } = event.target
    if (name === 'staff') {
      setValues((prev) => ({ ...prev, staff: value, date: '', start_time: '' }))
      setErrors((prev) => ({ ...prev, staff: undefined, date: undefined, start_time: undefined }))
      return
    }
    setValues((prev) => ({ ...prev, [name]: value }))
  }

  const selectSlot = (date, start) => {
    setValues((prev) => ({ ...prev, date, start_time: start }))
    setErrors((prev) => ({ ...prev, date: undefined, start_time: undefined }))
  }

  const submit = async (event) => {
    event.preventDefault()
    const full = { ...values, patient: patient?.id }
    const found = validateBooking(full, { needsPatient })
    setErrors(found)
    setFormError('')
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      const booked = await bookAppointment(bookingPayload(full, { needsPatient }))
      const flash = `Appointment booked for ${formatWhen(booked.start_time)} with ${booked.staff_name}.`
      if (portal) navigate('/my-appointments', { state: { flash } })
      else navigate(`/appointments?date=${dateKey(booked.start_time)}&staff=${booked.staff}`, { state: { flash } })
    } catch (error) {
      const { form, ...rest } = fieldErrors(error)
      setErrors(rest)
      setFormError(form || (Object.keys(rest).length ? '' : getErrorMessage(error, 'Could not book the appointment.')))
      // The slot may have just been taken: clear it so the list reloads.
      if (rest.start_time) setValues((prev) => ({ ...prev, date: '', start_time: '' }))
    } finally {
      setSaving(false)
    }
  }

  const back = portal ? { to: '/my-appointments', label: 'My appointments' } : { to: '/appointments', label: 'Appointments' }

  return (
    <>
      <PageHeader back={back} eyebrow="Scheduling" title="Book appointment" />
      <Panel>
        <form onSubmit={submit} noValidate className="form-stack appt-form">
          {formError && <Alert variant="error">{formError}</Alert>}
          {doctorsError && <Alert variant="error">{getErrorMessage(doctorsError, 'Could not load doctors.')}</Alert>}
          {needsPatient && (
            <PatientPicker value={patient} error={errors.patient}
              onChange={(p) => { setPatient(p); setErrors((prev) => ({ ...prev, patient: undefined })) }} />
          )}
          <SelectField label="Doctor" name="staff" value={values.staff} onChange={change} placeholder="Choose a doctor"
            options={doctors.map((d) => ({ value: String(d.staff_id), label: doctorLabel(d) }))} error={errors.staff} />
          <DoctorAvailability staff={values.staff} value={values.start_time} onSelect={selectSlot} />
          <div className="field" aria-live="polite">
            <p className="field__label">Appointment date</p>
            <p className="appt-booking-date">
              {values.date ? formatDayTitle(values.date) : 'Choose an available slot to set the date.'}
            </p>
            {errors.date && <p className="field__error">{errors.date}</p>}
          </div>
          {errors.start_time && <p className="field__error">{errors.start_time}</p>}
          <SelectField label="Type of visit" name="appointment_type" value={values.appointment_type} onChange={change}
            options={toOptions(BOOKABLE_APPOINTMENT_TYPE_LABELS)} error={errors.appointment_type} />
          <TextAreaField label="Reason for the visit (optional)" name="reason" value={values.reason} onChange={change}
            rows={3} maxLength={2000} error={errors.reason} />
          <div className="form-actions">
            <Button variant="secondary" onClick={() => navigate(back.to)}>Cancel</Button>
            <Button type="submit" loading={saving}>Book appointment</Button>
          </div>
        </form>
      </Panel>
    </>
  )
}
