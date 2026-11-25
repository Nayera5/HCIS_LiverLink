// Imaging orders: labels, form checks and allowed actions (no React, so `npm test` can import it).
// Mirrors apps/radiology; the backend is the authority.

export const IMAGING_STATUS = {
  ordered: { label: 'Ordered', tone: 'info' },
  scheduled: { label: 'Scheduled', tone: 'warning' },
  acquired: { label: 'Acquired', tone: 'success' },
  cancelled: { label: 'Cancelled', tone: 'neutral' },
}

export const BOOKING_STATE = {
  none: 'Not booked', pending: 'Awaiting confirmation', confirmed: 'Confirmed', done: 'Done',
}

// Follow-up filters of the orders list.
export const BOOKING_OPTIONS = [
  { value: 'none', label: 'Not booked yet' },
  { value: 'pending', label: 'Awaiting confirmation' },
]

export const MAX_INDICATION = 2000

// What every imaging dropdown asks the Billing API for. Examinations are never listed in this code.
export const ACTIVE_IMAGING_SERVICES = { category: 'imaging', active_only: 'true' }
export const ALL_IMAGING_SERVICES = { category: 'imaging' } // list filters: older orders may use inactive services

/** Dropdown options, one per service: only its name (no price or other billing information). */
export function imagingServiceOptions(services) {
  return services.map((service) => ({ value: String(service.id), label: service.name }))
}

/** Link to the order form for a known patient. `from`: 'patient' when opened on the patient page. */
export function newOrderLink({ patientId, encounterId, from }) {
  const params = new URLSearchParams({ patient: String(patientId) })
  if (encounterId) params.set('encounter', String(encounterId))
  else if (from) params.set('from', from)
  return `/imaging/orders/new?${params}`
}

/** Where the order form was opened: its back link, and whether the patient is fixed. */
export function orderOrigin(searchParams) {
  const patient = searchParams.get('patient')
  const encounter = searchParams.get('encounter')
  const from = patient && searchParams.get('from')
  if (patient && encounter) return { to: `/encounters/${encounter}`, label: 'Encounter', fixed: true }
  if (from === 'patient') return { to: `/patients/${patient}`, label: 'Patient', fixed: true }
  return { to: '/imaging/orders', label: 'Imaging orders', fixed: false }
}

export const STATUS_OPTIONS = Object.entries(IMAGING_STATUS).map(([value, { label }]) => ({ value, label }))

const blank = (value) => !String(value ?? '').trim()

export function validateImagingOrder(values) {
  const errors = {}
  if (blank(values.billing_service)) errors.billing_service = 'Choose the imaging type.'
  if (blank(values.clinical_indication)) errors.clinical_indication = 'Write the clinical indication.'
  else if (values.clinical_indication.trim().length > MAX_INDICATION) {
    errors.clinical_indication = `Use at most ${MAX_INDICATION} characters.`
  }
  return errors
}

export function imagingOrderPayload(values, patientId) {
  const payload = {
    patient: Number(patientId),
    billing_service: Number(values.billing_service),
    clinical_indication: values.clinical_indication.trim(),
  }
  if (values.encounter) payload.encounter = Number(values.encounter)
  return payload
}

/**
 * Which buttons to show for an order. `can` is the auth helper. Radiologists manage the order;
 * doctors cancel their own (`can_cancel` comes from the API); coordinators only remind the patient.
 */
export function imagingActions(order, can, now = new Date()) {
  const active = order.status === 'ordered' || order.status === 'scheduled'
  const manage = active && can('imaging.manage')
  const booked = order.appointment_status === 'booked'
  const checkedIn = order.appointment_status === 'checked_in'
  const started = Boolean(order.appointment_start) && new Date(order.appointment_start) <= now
  return {
    confirm: manage && order.booking_state === 'pending' && !started,
    book: manage && !checkedIn,
    cancelBooking: manage && (booked || checkedIn),
    noShow: manage && booked && started,
    acquire: manage,
    cancel: active && Boolean(order.can_cancel),
    remind: active && can('imaging.coordinate') && Boolean(order.patient_has_portal),
  }
}

/** Patient portal: choose / move or cancel the scan appointment (until it starts or check-in). */
export function patientScanActions(order, now = new Date()) {
  const active = order.status === 'ordered' || order.status === 'scheduled'
  const changeable = order.appointment_status === 'booked' && new Date(order.appointment_start) > now
  return { choose: active && (!order.appointment || changeable), cancel: active && changeable }
}

export function slotState(slot) {
  if (slot.booking) {
    if (slot.booking.status === 'completed') return { label: 'Done', tone: 'success' }
    return slot.booking.order_status === 'ordered'
      ? { label: 'Awaiting confirmation', tone: 'warning' } : { label: 'Booked', tone: 'info' }
  }
  return slot.is_published ? { label: 'Published', tone: 'success' } : { label: 'Not published', tone: 'neutral' }
}

export function validateSlots(values) {
  const errors = {}
  if (blank(values.billing_service)) errors.billing_service = 'Choose the imaging type.'
  if (blank(values.date)) errors.date = 'Choose a date.'
  if (blank(values.start_time)) errors.start_time = 'Enter the start time.'
  if (blank(values.end_time)) errors.end_time = 'Enter the end time.'
  else if (values.end_time <= values.start_time) errors.end_time = 'End time must be after start time.'
  const minutes = Number(values.slot_minutes)
  if (!Number.isInteger(minutes) || minutes < 5 || minutes > 240) errors.slot_minutes = 'Enter 5 to 240 minutes.'
  return errors
}
