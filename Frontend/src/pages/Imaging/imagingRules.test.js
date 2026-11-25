import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import { loadAllPages } from '../../api/pagination.js'
import {
  ACTIVE_IMAGING_SERVICES, imagingActions, imagingOrderPayload, imagingServiceOptions, newOrderLink, orderOrigin, patientScanActions, slotState, validateImagingOrder,
  validateSlots,
} from './imagingRules.js'

const valid = { billing_service: '12', clinical_indication: ' Suspected HCC ', encounter: '' }

describe('imaging order form', () => {
  test('requires the service and the indication', () => {
    assert.deepEqual(Object.keys(validateImagingOrder({ billing_service: '', clinical_indication: '  ' })),
      ['billing_service', 'clinical_indication'])
    assert.deepEqual(validateImagingOrder(valid), {})
  })

  test('limits the indication length', () => {
    assert.ok(validateImagingOrder({ ...valid, clinical_indication: 'x'.repeat(2001) }).clinical_indication)
  })

  test('payload trims text and leaves out empty links', () => {
    assert.deepEqual(imagingOrderPayload(valid, '7'),
      { patient: 7, billing_service: 12, clinical_indication: 'Suspected HCC' })
    const linked = imagingOrderPayload({ ...valid, encounter: '3' }, 7)
    assert.equal(linked.encounter, 3)
  })

  test('options show only the catalog name', () => {
    assert.deepEqual(imagingServiceOptions([
      { id: 14, code: 'IMG-NEW', name: 'New active scan', price: '1250.00' },
    ]), [{ value: '14', label: 'New active scan' }])
  })

  test('the dropdown has exactly the active imaging services of the Billing API, across pages', async () => {
    const catalog = Array.from({ length: 230 }, (_, i) => ({
      id: i + 1, code: `S-${i}`, name: `Service ${i}`, price: '1.00',
      category: i % 2 ? 'imaging' : 'lab', is_active: i % 5 !== 0,
    }))
    const api = async ({ category, active_only: activeOnly, page, page_size: size }) => {
      const rows = catalog.filter((s) => s.category === category && (activeOnly !== 'true' || s.is_active))
      return { results: rows.slice((page - 1) * 40, page * 40), next: page * 40 < rows.length ? 'next' : null, size }
    }
    const options = imagingServiceOptions(await loadAllPages(api, ACTIVE_IMAGING_SERVICES))
    const expected = catalog.filter((s) => s.category === 'imaging' && s.is_active)
    assert.deepEqual(options, expected.map((s) => ({ value: String(s.id), label: s.name })))
  })
})

describe('where an order is started', () => {
  const origin = (link) => orderOrigin(new URLSearchParams(link.split('?')[1]))

  test('from a patient page or encounter the patient is fixed', () => {
    assert.deepEqual(origin(newOrderLink({ patientId: 7, from: 'patient' })),
      { to: '/patients/7', label: 'Patient', fixed: true })
    const link = newOrderLink({ patientId: 7, encounterId: 3 })
    assert.equal(link, '/imaging/orders/new?patient=7&encounter=3')
    assert.deepEqual(origin(link), { to: '/encounters/3', label: 'Encounter', fixed: true })
  })

  test('from the imaging orders page the patient can be changed', () => {
    for (const query of ['', 'patient=7', 'from=patient', 'encounter=3']) {
      assert.deepEqual(orderOrigin(new URLSearchParams(query)),
        { to: '/imaging/orders', label: 'Imaging orders', fixed: false })
    }
  })
})

const NOW = new Date('2026-11-25T10:00:00Z')
const booked = (over = {}) => ({
  status: 'ordered', booking_state: 'pending', appointment: 4, appointment_status: 'booked',
  appointment_start: '2026-11-26T09:00:00Z', can_cancel: false, patient_has_portal: true, ...over,
})
const unbooked = (over = {}) => ({
  status: 'ordered', booking_state: 'none', appointment: null, appointment_status: null, appointment_start: null,
  can_cancel: false, patient_has_portal: true, ...over,
})
const on = (actions) => Object.keys(actions).filter((key) => actions[key])

describe('imaging order actions', () => {
  const only = (cap) => (c) => c === cap

  test('radiologist manages the order', () => {
    const manage = only('imaging.manage')
    assert.deepEqual(on(imagingActions(unbooked({ can_cancel: true }), manage, NOW)), ['book', 'acquire', 'cancel'])
    assert.deepEqual(on(imagingActions(booked(), manage, NOW)), ['confirm', 'book', 'cancelBooking', 'acquire'])
    assert.deepEqual(on(imagingActions(booked({ status: 'scheduled', booking_state: 'confirmed' }), manage, NOW)),
      ['book', 'cancelBooking', 'acquire'])
    assert.deepEqual(on(imagingActions(booked({ appointment_start: '2026-11-25T09:00:00Z' }), manage, NOW)),
      ['book', 'cancelBooking', 'noShow', 'acquire'])
    assert.deepEqual(on(imagingActions(booked({
      status: 'scheduled', booking_state: 'confirmed', appointment_status: 'checked_in',
    }), manage, NOW)), ['cancelBooking', 'acquire'])
  })

  test('coordinator only reminds; doctors only cancel their own', () => {
    assert.deepEqual(on(imagingActions(booked(), only('imaging.coordinate'), NOW)), ['remind'])
    assert.deepEqual(on(imagingActions(booked({ patient_has_portal: false }), only('imaging.coordinate'), NOW)), [])
    assert.deepEqual(on(imagingActions(booked({ can_cancel: true }), only('imaging.order'), NOW)), ['cancel'])
    assert.deepEqual(on(imagingActions(booked(), only('imaging.order'), NOW)), [])
  })

  test('finished orders have no actions', () => {
    for (const status of ['acquired', 'cancelled']) {
      assert.deepEqual(on(imagingActions(booked({ status, booking_state: 'done' }), () => true, NOW)), [])
    }
  })
})

describe('patient scan actions', () => {
  test('choose, change and cancel until the scan starts or check-in', () => {
    assert.deepEqual(on(patientScanActions(unbooked(), NOW)), ['choose'])
    assert.deepEqual(on(patientScanActions(booked(), NOW)), ['choose', 'cancel'])
    assert.deepEqual(on(patientScanActions(booked({ appointment_status: 'checked_in' }), NOW)), [])
    assert.deepEqual(on(patientScanActions(booked({ appointment_start: '2026-11-25T09:00:00Z' }), NOW)), [])
    assert.deepEqual(on(patientScanActions(unbooked({ status: 'cancelled' }), NOW)), [])
  })
})

describe('scan slots', () => {
  test('state labels', () => {
    assert.equal(slotState({ is_published: true }).label, 'Published')
    assert.equal(slotState({ is_published: false }).label, 'Not published')
    assert.equal(slotState({ booking: { order_status: 'ordered', status: 'booked' } }).label, 'Awaiting confirmation')
    assert.equal(slotState({ booking: { order_status: 'scheduled', status: 'booked' } }).label, 'Booked')
    assert.equal(slotState({ booking: { order_status: 'acquired', status: 'completed' } }).label, 'Done')
  })

  test('form checks', () => {
    const ok = { billing_service: '12', date: '2026-11-28', start_time: '09:00', end_time: '11:00', slot_minutes: '30' }
    assert.deepEqual(validateSlots(ok), {})
    assert.deepEqual(Object.keys(validateSlots({ ...ok, billing_service: '', date: '', end_time: '08:00', slot_minutes: '0' })),
      ['billing_service', 'date', 'end_time', 'slot_minutes'])
  })
})
