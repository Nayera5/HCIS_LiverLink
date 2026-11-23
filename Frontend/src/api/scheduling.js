// Scheduling API (backend: apps/scheduling/views.py, mounted at /api/scheduling/). Permissions are
// enforced server-side: portal users only see and book their own appointments (no patient id needed).
import { authRequest, toQuery } from './http'

// --- Doctors and schedules ---------------------------------------------------------
/** Doctors who can be booked: [{ staff_id, name, job_title, is_me }] */
export function listDoctors() {
  return authRequest('/scheduling/schedules/doctors/')
}

/** params: { staff, day_of_week, is_active } */
export function listSchedules(params = {}) {
  return authRequest(`/scheduling/schedules/${toQuery(params)}`)
}

/** data: { staff (super admin only), day_of_week, start_time, end_time, slot_minutes, is_active } */
export function createSchedule(data) {
  return authRequest('/scheduling/schedules/', { method: 'POST', body: data })
}

/** Schedules are never deleted: send { is_active: false } to hide one. */
export function updateSchedule(id, changes) {
  return authRequest(`/scheduling/schedules/${id}/`, { method: 'PATCH', body: changes })
}

/** Free slots of a doctor on one day: { staff, date, slots: [{ start_time, end_time }] } */
export function getFreeSlots(staff, date) {
  return authRequest(`/scheduling/schedules/free-slots/${toQuery({ staff, date })}`)
}

// --- Appointments ----------------------------------------------------------------------
/** params: { staff, patient, status, appointment_type, date_from, date_to } (dates YYYY-MM-DD) */
export function listAppointments(params = {}) {
  return authRequest(`/scheduling/appointments/${toQuery(params)}`)
}

/** data: { patient (staff only), staff, appointment_type, start_time (a free slot), reason } */
export function bookAppointment(data) {
  return authRequest('/scheduling/appointments/', { method: 'POST', body: data })
}

/** data: { start_time, staff (optional) } */
export function rescheduleAppointment(id, data) {
  return authRequest(`/scheduling/appointments/${id}/reschedule/`, { method: 'POST', body: data })
}

const STATUS_PATHS = { cancel: 'cancel', check_in: 'check-in', no_show: 'no-show', complete: 'complete' }

/** action: 'cancel' | 'check_in' | 'no_show' | 'complete' */
export function changeAppointmentStatus(id, action) {
  return authRequest(`/scheduling/appointments/${id}/${STATUS_PATHS[action]}/`, { method: 'POST' })
}
