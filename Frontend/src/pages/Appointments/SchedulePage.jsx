import { useCallback, useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import { createSchedule, listDoctors, listSchedules, updateSchedule } from '../../api/scheduling'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { ClockIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import {
  CLINIC_TIME_ZONE, DAY_LABELS, doctorLabel, findMyStaffId, groupSchedules, schedulePayload, shortTime, toOptions, validateSchedule,
} from './appointmentRules'

const EMPTY = { day_of_week: 'sat', start_time: '09:00', end_time: '13:00', slot_minutes: '30' }

/** Add or edit one block of working hours. */
function ScheduleForm({ initial = EMPTY, staffId, scheduleId, onSaved, onCancel }) {
  const [values, setValues] = useState({ ...initial, start_time: shortTime(initial.start_time),
    end_time: shortTime(initial.end_time), slot_minutes: String(initial.slot_minutes) })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const change = (e) => setValues((prev) => ({ ...prev, [e.target.name]: e.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    const found = validateSchedule(values)
    setErrors(found)
    setFormError('')
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      const body = schedulePayload({ ...values, is_active: initial.is_active }, staffId)
      onSaved(scheduleId ? await updateSchedule(scheduleId, body) : await createSchedule(body))
    } catch (error) {
      const { form, ...rest } = fieldErrors(error)
      setErrors(rest)
      setFormError(form || (Object.keys(rest).length ? '' : getErrorMessage(error, 'Could not save the schedule.')))
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate className="form-stack appt-schedule-form">
      {formError && <Alert variant="error">{formError}</Alert>}
      <div className="appt-schedule-grid">
        <SelectField label="Day" name="day_of_week" value={values.day_of_week} onChange={change}
          options={toOptions(DAY_LABELS)} error={errors.day_of_week} />
        <TextField label="From" name="start_time" type="time" value={values.start_time} onChange={change}
          error={errors.start_time} />
        <TextField label="To" name="end_time" type="time" value={values.end_time} onChange={change}
          error={errors.end_time} />
        <TextField label="Slot (minutes)" name="slot_minutes" type="number" min="5" step="5"
          value={values.slot_minutes} onChange={change} error={errors.slot_minutes} />
      </div>
      <div className="form-actions">
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button type="submit" loading={saving}>{scheduleId ? 'Save changes' : 'Add working hours'}</Button>
      </div>
    </form>
  )
}

/**
 * Doctor availability (spec §3). Doctors (schedules.manage_own) edit their own working hours;
 * super admin (schedules.manage_all) chooses the doctor. Schedules are switched off, never deleted.
 */
export default function SchedulePage() {
  const { can } = useAuth()
  const manageAll = can('schedules.manage_all')
  const { data: doctorRows, loading: doctorsLoading } = useApi(listDoctors)
  const doctors = doctorRows || []
  const myStaffId = findMyStaffId(doctors)
  const [chosen, setChosen] = useState('')
  const staffId = manageAll ? chosen || (doctors[0] ? String(doctors[0].staff_id) : '') : myStaffId ? String(myStaffId) : ''

  const loader = useCallback(
    () => (staffId ? listSchedules({ staff: staffId }) : Promise.resolve([])),
    [staffId],
  )
  const { data, error, loading, reload } = useApi(loader)
  const [editing, setEditing] = useState(null) // 'new' or a schedule_id
  const [actionError, setActionError] = useState('')

  const saved = () => {
    setEditing(null)
    reload()
  }

  const toggle = async (schedule) => {
    setActionError('')
    try {
      await updateSchedule(schedule.schedule_id, { is_active: !schedule.is_active })
      reload()
    } catch (err) {
      setActionError(fieldErrors(err).form || getErrorMessage(err, 'Could not change the schedule.'))
    }
  }

  const groups = groupSchedules(data || [])

  return (
    <>
      <PageHeader eyebrow="Scheduling" title={manageAll ? 'Doctor schedules' : 'My schedule'}
        actions={staffId && editing !== 'new' && <Button onClick={() => setEditing('new')}>Add working hours</Button>} />
      <p className="muted-text form-alert">
        Patients can book the free slots inside these hours. Times are in the clinic time zone ({CLINIC_TIME_ZONE}).
      </p>
      {manageAll && (
        <SelectField label="Doctor" className="appt-toolbar__doctor form-alert" value={staffId}
          onChange={(e) => { setChosen(e.target.value); setEditing(null) }}
          options={doctors.map((d) => ({ value: String(d.staff_id), label: doctorLabel(d) }))} />
      )}
      {!doctorsLoading && !staffId && (
        <Alert variant="info">{manageAll ? 'There are no doctors to schedule yet.' : 'Your account has no doctor profile.'}</Alert>
      )}
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load the schedule.')}</Alert>}
      {actionError && <Alert variant="error" className="form-alert">{actionError}</Alert>}

      {staffId && (
        <Panel title="Working hours" subtitle="Each block is split into bookable slots.">
          {editing === 'new' && (
            <ScheduleForm staffId={manageAll ? staffId : null} onSaved={saved} onCancel={() => setEditing(null)} />
          )}
          {loading && !data ? <LoadingBlock label="Loading schedule" /> : groups.length ? (
            <div className="emr-groups">
              {groups.map((group) => (
                <section key={group.day}>
                  <h3 className="emr-group__title">{group.label}</h3>
                  <ul className="emr-list">
                    {group.items.map((s) => (
                      <li key={s.schedule_id} className="emr-list__item emr-list__item--stacked">
                        {editing === s.schedule_id ? (
                          <ScheduleForm initial={s} scheduleId={s.schedule_id} staffId={manageAll ? staffId : null}
                            onSaved={saved} onCancel={() => setEditing(null)} />
                        ) : (
                          <div className="appt-schedule-row">
                            <div>
                              <span className="cell-primary">{shortTime(s.start_time)}–{shortTime(s.end_time)}</span>
                              <span className="muted-text"> · {s.slot_minutes}-minute slots</span>
                            </div>
                            <div className="emr-actions">
                              <Badge tone={s.is_active ? 'success' : 'neutral'}>{s.is_active ? 'Active' : 'Off'}</Badge>
                              <Button size="sm" variant="secondary" onClick={() => setEditing(s.schedule_id)}>Edit</Button>
                              <Button size="sm" variant="secondary" onClick={() => toggle(s)}>
                                {s.is_active ? 'Turn off' : 'Turn on'}
                              </Button>
                            </div>
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          ) : editing !== 'new' && (
            <EmptyState icon={ClockIcon} title="No working hours yet">
              Add the days and times when patients can book.
            </EmptyState>
          )}
        </Panel>
      )}
    </>
  )
}
