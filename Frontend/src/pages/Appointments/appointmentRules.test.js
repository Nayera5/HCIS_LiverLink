// Run with `npm test` (Node's built-in test runner; no extra dependencies).
import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import {
  addDays, allowedActions, bookingPayload, calendarDays, calendarRange, dateKey, formatTime, formatDayTitle, groupByDay,
  groupSchedules, nextDateOf, schedulePayload, splitUpcoming, validateBooking, validateSchedule, weekStart,
} from './appointmentRules.js'

const canAll = (caps) => (cap) => caps.includes(cap)
const appt = (over = {}) => ({
  appointment_id: 1, staff: 5, status: 'booked', encounter: null,
  start_time: '2026-11-28T09:00:00Z', end_time: '2026-11-28T09:30:00Z', ...over,
})

describe('dates', () => {
  test('addDays crosses months', () => {
    assert.equal(addDays('2026-11-30', 1), '2026-12-01')
    assert.equal(addDays('2026-12-01', -1), '2026-11-30')
  })

  test('the week runs Saturday to Friday', () => {
    assert.equal(weekStart('2026-11-28'), '2026-11-28') // Saturday
    assert.equal(weekStart('2026-12-04'), '2026-11-28') // Friday
    assert.equal(weekStart('2026-11-29'), '2026-11-28') // Sunday
    const week = calendarDays('week', '2026-12-01')
    assert.equal(week.length, 7)
    assert.deepEqual(calendarRange('week', '2026-12-01'), { date_from: '2026-11-28', date_to: '2026-12-04' })
    assert.deepEqual(calendarRange('day', '2026-12-01'), { date_from: '2026-12-01', date_to: '2026-12-01' })
  })

  test('times use the clinic time zone (UTC)', () => {
    assert.equal(dateKey('2026-11-28T23:30:00Z'), '2026-11-28')
    assert.equal(formatTime('2026-11-28T09:05:00Z'), '09:05')
  })

  test('groupByDay sorts each day and keeps empty days', () => {
    const groups = groupByDay([appt({ appointment_id: 2, start_time: '2026-11-28T10:00:00Z' }), appt()],
      ['2026-11-28', '2026-11-29'])
    assert.deepEqual(groups.map((g) => g.items.map((a) => a.appointment_id)), [[1, 2], []])
  })
})

describe('allowed actions', () => {
  test('coordinator manages, checks in and completes', () => {
    const can = canAll(['appointments.book_any', 'appointments.check_in'])
    assert.deepEqual(allowedActions(appt(), { can }), ['reschedule', 'cancel', 'check_in', 'no_show'])
    assert.deepEqual(allowedActions(appt({ status: 'checked_in' }), { can }), ['cancel', 'complete'])
    assert.deepEqual(allowedActions(appt({ status: 'completed' }), { can }), [])
  })

  test('doctor completes own visit and starts or opens the encounter', () => {
    const can = canAll(['appointments.view', 'emr.write'])
    assert.deepEqual(allowedActions(appt(), { can, myStaffId: 5 }), [])
    assert.deepEqual(allowedActions(appt({ status: 'checked_in' }), { can, myStaffId: 5 }),
      ['complete', 'start_encounter'])
    assert.deepEqual(allowedActions(appt({ status: 'checked_in' }), { can, myStaffId: 6 }), [])
    assert.deepEqual(allowedActions(appt({ status: 'completed', encounter: 9 }), { can, myStaffId: 5 }),
      ['open_encounter'])
  })

  test('patients reschedule and cancel their own booking only', () => {
    const can = canAll(['self.appointments'])
    assert.deepEqual(allowedActions(appt(), { can, portal: true }), ['reschedule', 'cancel'])
    assert.deepEqual(allowedActions(appt({ status: 'no_show', encounter: 3 }), { can, portal: true }), [])
  })
})

test('splitUpcoming: active future visits first, the rest newest first', () => {
  const now = new Date('2026-11-28T12:00:00Z')
  const list = [
    appt({ appointment_id: 1, start_time: '2026-11-27T09:00:00Z', end_time: '2026-11-27T09:30:00Z' }),
    appt({ appointment_id: 2, start_time: '2026-12-02T09:00:00Z', end_time: '2026-12-02T09:30:00Z' }),
    appt({ appointment_id: 3, start_time: '2026-11-30T09:00:00Z', end_time: '2026-11-30T09:30:00Z' }),
    appt({ appointment_id: 4, status: 'cancelled', start_time: '2026-12-05T09:00:00Z', end_time: '2026-12-05T09:30:00Z' }),
  ]
  const { upcoming, past } = splitUpcoming(list, now)
  assert.deepEqual(upcoming.map((a) => a.appointment_id), [3, 2])
  assert.deepEqual(past.map((a) => a.appointment_id), [4, 1])
})

describe('booking form', () => {
  test('staff must choose a patient; portal users do not', () => {
    const empty = { staff: '', appointment_type: '', date: '', start_time: '' }
    assert.deepEqual(Object.keys(validateBooking(empty, { needsPatient: true })).sort(),
      ['appointment_type', 'date', 'patient', 'staff', 'start_time'])
    assert.ok(!validateBooking(empty, { needsPatient: false }).patient)
    const ok = { patient: '3', staff: '5', appointment_type: 'consultation', date: '2026-11-28',
      start_time: '2026-11-28T09:00:00Z' }
    assert.deepEqual(validateBooking(ok, { needsPatient: true }), {})
  })

  test('payload converts ids and trims the reason', () => {
    const values = { patient: '3', staff: '5', appointment_type: 'ct_scan', start_time: 'T', reason: '  pain ' }
    assert.deepEqual(bookingPayload(values, { needsPatient: true }),
      { patient: 3, staff: 5, appointment_type: 'ct_scan', start_time: 'T', reason: 'pain' })
    assert.equal(bookingPayload(values, { needsPatient: false }).patient, undefined)
  })
})

describe('schedule form', () => {
  test('end after start; slot positive and within the hours', () => {
    assert.ok(validateSchedule({ day_of_week: 'sat', start_time: '12:00', end_time: '09:00', slot_minutes: 30 }).end_time)
    assert.ok(validateSchedule({ day_of_week: 'sat', start_time: '09:00', end_time: '10:00', slot_minutes: 0 }).slot_minutes)
    assert.ok(validateSchedule({ day_of_week: 'sat', start_time: '09:00', end_time: '09:20', slot_minutes: 30 }).slot_minutes)
    assert.ok(validateSchedule({ day_of_week: 'xyz', start_time: '09:00', end_time: '10:00', slot_minutes: 30 }).day_of_week)
    assert.deepEqual(validateSchedule({ day_of_week: 'sat', start_time: '09:00', end_time: '11:00', slot_minutes: '30' }), {})
  })

  test('next date of each schedule day (today counts)', () => {
    const today = '2026-11-25' // a Wednesday
    assert.deepEqual(['wed', 'thu', 'fri', 'sat', 'sun', 'mon', 'tue'].map((day) => nextDateOf(day, today)),
      ['2026-11-25', '2026-11-26', '2026-11-27', '2026-11-28', '2026-11-29', '2026-11-30', '2026-12-01'])
    assert.equal(nextDateOf('fri', '2026-12-26'), '2027-01-01') // Saturday, across the year end
    assert.match(formatDayTitle(nextDateOf('sat', today)), /^Saturday,? 28 November 2026$/)
  })

  test('payload and grouping', () => {
    assert.deepEqual(schedulePayload({ day_of_week: 'mon', start_time: '09:00:00', end_time: '11:00', slot_minutes: '15' }, 4),
      { staff: 4, day_of_week: 'mon', start_time: '09:00', end_time: '11:00', slot_minutes: 15, is_active: true })
    const groups = groupSchedules([
      { day_of_week: 'mon', start_time: '13:00:00' }, { day_of_week: 'sat', start_time: '09:00:00' },
      { day_of_week: 'mon', start_time: '09:00:00' },
    ])
    assert.deepEqual(groups.map((g) => g.day), ['sat', 'mon'])
    assert.deepEqual(groups[1].items.map((s) => s.start_time), ['09:00:00', '13:00:00'])
  })
})
