// Appointments: labels, allowed actions, calendar dates and form checks (no React, so `npm test`
// can import it). Mirrors apps/scheduling (models.py, serializers.py, views.py); the backend is the authority.

export const APPOINTMENT_TYPE_LABELS = {
  consultation: 'Consultation',
  ct_scan: 'CT scan',
  lab_visit: 'Lab visit',
  donor_evaluation: 'Donor evaluation',
  recipient_evaluation: 'Recipient evaluation',
  follow_up: 'Post-transplant follow-up',
  imaging: 'Imaging scan',
}

// Visits booked with a doctor. Scans are booked from an imaging order instead (pages/Imaging).
export const BOOKABLE_TYPE_LABELS = Object.fromEntries(
  Object.entries(APPOINTMENT_TYPE_LABELS).filter(([type]) => type !== 'ct_scan' && type !== 'imaging'),
)

export const APPOINTMENT_STATUS = {
  booked: { label: 'Booked', tone: 'info' },
  checked_in: { label: 'Checked in', tone: 'warning' },
  completed: { label: 'Completed', tone: 'success' },
  no_show: { label: 'No-show', tone: 'danger' },
  cancelled: { label: 'Cancelled', tone: 'neutral' },
}

// Week starts on Saturday, as in the schedule's day order.
export const DAY_LABELS = {
  sat: 'Saturday', sun: 'Sunday', mon: 'Monday', tue: 'Tuesday', wed: 'Wednesday', thu: 'Thursday', fri: 'Friday',
}

export const JOB_TITLE_LABELS = {
  hepatologist: 'Hepatologist',
  transplant_surgeon: 'Transplant surgeon',
  radiologist: 'Radiologist',
}

// The backend works out schedule slots and date filters in its TIME_ZONE (Backend/config/settings.py).
// All appointment times are shown in the same zone so that they match the doctors' working hours.
export const CLINIC_TIME_ZONE = 'UTC'

const blank = (value) => value === undefined || value === null || String(value).trim() === ''

/** Options for a <SelectField> from a { value: label } map. */
export function toOptions(labels) {
  return Object.entries(labels).map(([value, label]) => ({ value, label }))
}

/** The signed-in doctor's staff id from the doctors list (`is_me`), or null. */
export function findMyStaffId(doctors = []) {
  const me = doctors.find((d) => d.is_me)
  return me ? me.staff_id : null
}

/** Replace one appointment in a list after an action. */
export function replaceRow(list, updated) {
  return (list || []).map((a) => (a.appointment_id === updated.appointment_id ? updated : a))
}

export function doctorLabel(doctor) {
  return `${doctor.name} · ${JOB_TITLE_LABELS[doctor.job_title] || doctor.job_title}`
}

// --- Dates (plain 'YYYY-MM-DD' strings; no time-zone surprises) ---------------------------------
const DATE_PARTS = new Intl.DateTimeFormat('en-CA', {
  timeZone: CLINIC_TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit',
})
const TIME = new Intl.DateTimeFormat('en-GB', { timeZone: CLINIC_TIME_ZONE, hour: '2-digit', minute: '2-digit' })
const DAY_TITLE = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'UTC', weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
})
const DAY_SHORT = new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', weekday: 'short', day: 'numeric', month: 'short' })

const toUtc = (iso) => new Date(`${iso}T00:00:00Z`)

/** The clinic's date ('YYYY-MM-DD') of a moment (Date or ISO datetime string). */
export function dateKey(value = new Date()) {
  return DATE_PARTS.format(new Date(value))
}

export function addDays(iso, days) {
  const date = toUtc(iso)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

/** The Saturday on or before `iso`. */
export function weekStart(iso) {
  const day = toUtc(iso).getUTCDay() // Sunday = 0 ... Saturday = 6
  return addDays(iso, -((day + 1) % 7))
}

/** The next date ('YYYY-MM-DD') of a schedule day ('sat' ... 'fri'); today counts. */
export function nextDateOf(day, today = dateKey()) {
  const date = addDays(weekStart(today), Object.keys(DAY_LABELS).indexOf(day))
  return date < today ? addDays(date, 7) : date
}

/** The dates shown by the calendar: one day, or Saturday to Friday. */
export function calendarDays(view, iso) {
  if (view === 'day') return [iso]
  const start = weekStart(iso)
  return Array.from({ length: 7 }, (_, i) => addDays(start, i))
}

/** Query filters for the calendar (the backend filters by start date, inclusive). */
export function calendarRange(view, iso) {
  const days = calendarDays(view, iso)
  return { date_from: days[0], date_to: days[days.length - 1] }
}

/** Appointments grouped under each calendar day (sorted by start time). */
export function groupByDay(appointments = [], days = []) {
  return days.map((date) => ({
    date,
    items: appointments
      .filter((a) => dateKey(a.start_time) === date)
      .sort((a, b) => new Date(a.start_time) - new Date(b.start_time)),
  }))
}

export function formatTime(value) {
  return value ? TIME.format(new Date(value)) : '—'
}

export function formatTimeRange(appointment) {
  return `${formatTime(appointment.start_time)}–${formatTime(appointment.end_time)}`
}

/** "Saturday, 28 November 2026" */
export function formatDayTitle(iso) {
  return DAY_TITLE.format(toUtc(iso))
}

/** "Sat 28 Nov" */
export function formatDayShort(iso) {
  return DAY_SHORT.format(toUtc(iso))
}

/** "28 Nov 2026, 09:30" in the clinic time zone. */
export function formatWhen(value) {
  return value ? `${DAY_SHORT.format(toUtc(dateKey(value)))} ${formatTime(value)}` : '—'
}

/** Schedule times come back as "09:00:00"; show "09:00". */
export function shortTime(value) {
  return value ? String(value).slice(0, 5) : '—'
}

// --- What the signed-in user may do with one appointment --------------------------------------
/**
 * @param appointment  row from the API
 * @param who  { can(capability), myStaffId, portal }  (`portal` = patient/donor account)
 * @returns list of action keys: reschedule, cancel, check_in, no_show, complete, start_encounter, open_encounter;
 *   imaging appointments only: check_in, open_order, manage_scan (the rest is done on the imaging order)
 */
export function allowedActions(appointment, { can, myStaffId = null, portal = false }) {
  const { status } = appointment
  const manages = portal || can('appointments.book_any') // the backend limits portal users to their own
  const coordinator = can('appointments.check_in')
  const isDoctor = myStaffId !== null && myStaffId === appointment.staff
  const actions = []
  if (appointment.imaging_order) {
    if (coordinator && status === 'booked') actions.push('check_in')
    if (portal) actions.push('manage_scan')
    else if (can('imaging.view')) actions.push('open_order')
    return actions
  }
  if (manages && status === 'booked') actions.push('reschedule')
  if (manages && (status === 'booked' || status === 'checked_in')) actions.push('cancel')
  if (coordinator && status === 'booked') actions.push('check_in', 'no_show')
  if ((isDoctor || coordinator) && status === 'checked_in') actions.push('complete')
  if (!portal && appointment.encounter) actions.push('open_encounter')
  else if (isDoctor && can('emr.write') && (status === 'checked_in' || status === 'completed')) {
    actions.push('start_encounter')
  }
  return actions
}

/** Upcoming (booked / checked in, not yet ended) and past appointments for the portal. */
export function splitUpcoming(appointments = [], now = new Date()) {
  const active = (a) => (a.status === 'booked' || a.status === 'checked_in') && new Date(a.end_time) > now
  const upcoming = appointments.filter(active).sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
  const past = appointments.filter((a) => !active(a)).sort((a, b) => new Date(b.start_time) - new Date(a.start_time))
  return { upcoming, past }
}

// --- Booking form ---------------------------------------------------------------------------
export function validateBooking(values, { needsPatient }) {
  const errors = {}
  if (needsPatient && blank(values.patient)) errors.patient = 'Choose the patient.'
  if (blank(values.staff)) errors.staff = 'Choose a doctor.'
  if (!BOOKABLE_TYPE_LABELS[values.appointment_type]) errors.appointment_type = 'Choose the type of visit.'
  if (blank(values.date)) errors.date = 'Choose a date.'
  if (blank(values.start_time)) errors.start_time = 'Choose a free time.'
  return errors
}

export function bookingPayload(values, { needsPatient }) {
  return {
    ...(needsPatient && { patient: Number(values.patient) }),
    staff: Number(values.staff),
    appointment_type: values.appointment_type,
    start_time: values.start_time,
    reason: blank(values.reason) ? '' : values.reason.trim(),
  }
}

// --- Doctor schedule form -------------------------------------------------------------------
const minutes = (hhmm) => {
  const [h, m] = String(hhmm).split(':').map(Number)
  return h * 60 + m
}

export function validateSchedule(values) {
  const errors = {}
  if (!DAY_LABELS[values.day_of_week]) errors.day_of_week = 'Choose a day.'
  if (blank(values.start_time)) errors.start_time = 'Enter the start time.'
  if (blank(values.end_time)) errors.end_time = 'Enter the end time.'
  else if (!errors.start_time && minutes(values.end_time) <= minutes(values.start_time)) {
    errors.end_time = 'End time must be after start time.'
  }
  const slot = Number(values.slot_minutes)
  if (!Number.isInteger(slot) || slot <= 0) errors.slot_minutes = 'Enter a whole number of minutes, more than 0.'
  else if (!errors.start_time && !errors.end_time && slot > minutes(values.end_time) - minutes(values.start_time)) {
    errors.slot_minutes = 'A slot cannot be longer than the working hours.'
  }
  return errors
}

export function schedulePayload(values, staffId) {
  return {
    ...(staffId && { staff: Number(staffId) }),
    day_of_week: values.day_of_week,
    start_time: shortTime(values.start_time),
    end_time: shortTime(values.end_time),
    slot_minutes: Number(values.slot_minutes),
    is_active: values.is_active !== false,
  }
}

/** Schedules grouped by weekday, in the order Saturday → Friday; empty days are dropped. */
export function groupSchedules(schedules = []) {
  return Object.keys(DAY_LABELS)
    .map((day) => ({
      day,
      label: DAY_LABELS[day],
      items: schedules.filter((s) => s.day_of_week === day).sort((a, b) => a.start_time.localeCompare(b.start_time)),
    }))
    .filter((group) => group.items.length > 0)
}
