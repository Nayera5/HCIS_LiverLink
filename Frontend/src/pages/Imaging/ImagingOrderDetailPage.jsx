import { useCallback, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import {
  bookScan, cancelScanBooking, changeImagingOrderStatus, getImagingOrder, listOrderSlots, markScanNoShow, remindPatient,
} from '../../api/imaging'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { ConfirmDialog, LoadingBlock } from '../../components/ui/Feedback'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import TextAreaField from '../../components/ui/TextAreaField'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { APPOINTMENT_STATUS, formatWhen } from '../Appointments/appointmentRules'
import { ImagingStatusBadge, ScanSlotPicker } from './imagingParts'
import { BOOKING_STATE, imagingActions } from './imagingRules'
import '../Patients/Patients.css'
import './Imaging.css'

const DIALOGS = {
  confirm: { title: 'Confirm the scan appointment?', confirm: 'Confirm scan', done: 'Scan confirmed.',
    text: 'The patient is told that the time is confirmed.' },
  book: { title: 'Choose a scan slot', confirm: 'Schedule scan', done: 'Scan scheduled.' },
  cancelBooking: { title: 'Cancel the scan appointment?', confirm: 'Cancel appointment', tone: 'danger',
    needsReason: true, done: 'Scan appointment cancelled.',
    text: 'The slot becomes free and the order can be booked again.' },
  noShow: { title: 'Mark as no-show?', confirm: 'Mark no-show', tone: 'danger', done: 'No-show recorded.',
    text: 'The order can be booked again.' },
  acquire: { title: 'Mark images as acquired?', confirm: 'Mark acquired', done: 'Order marked as acquired.',
    text: 'Confirm that the scan was performed. This cannot be undone.' },
  cancel: { title: 'Cancel this imaging order?', confirm: 'Cancel order', tone: 'danger', needsReason: true,
    done: 'Order cancelled.', text: 'Its scan appointment is cancelled too. This cannot be undone.' },
  remind: { title: 'Remind the patient?', confirm: 'Send reminder', done: 'Reminder sent.',
    text: 'The patient gets a notification about this scan (at most once a day).' },
}

const BUTTONS = [
  ['remind', 'Remind patient', 'primary'], ['confirm', 'Confirm scan', 'primary'], ['book', 'Schedule', 'secondary'],
  ['acquire', 'Mark acquired', 'secondary'], ['noShow', 'No-show', 'secondary'],
  ['cancelBooking', 'Cancel appointment', 'secondary'], ['cancel', 'Cancel order', 'danger'],
]

export default function ImagingOrderDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const { can } = useAuth()
  const loader = useCallback(() => getImagingOrder(id), [id])
  const { data: order, error, loading, setData, reload } = useApi(loader)
  const [flash, setFlash] = useState(location.state?.flash || '')
  const loadSlots = useCallback((params) => listOrderSlots(id, params), [id])
  const [target, setTarget] = useState(null) // the action being confirmed
  const [slot, setSlot] = useState('')
  const [reason, setReason] = useState('')
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const back = { to: '/imaging/orders', label: 'Imaging orders' }

  if (loading && !order) return <LoadingBlock label="Loading imaging order" />
  if (error && !order) {
    return (
      <>
        <PageHeader back={back} title="Imaging order" />
        <Alert variant="error">{getErrorMessage(error, 'Could not load this imaging order.')}</Alert>
      </>
    )
  }

  const actions = imagingActions(order, can)
  const dialog = DIALOGS[target] || {}
  const billingMessage = order.billing_state === 'needs_service'
    ? 'This imaging service is no longer active in the Billing catalog, so no invoice was generated. Follow up with Billing.'
    : order.billing_state === 'needs_review'
      ? 'The imaging invoice was not found. Review the Billing logs and create or correct the invoice if needed.'
      : ''

  const open = (action) => {
    setTarget(action)
    setSlot('')
    setReason('')
    setErrors({})
    setFlash('')
  }

  const run = () => {
    const pk = order.imaging_order_id
    switch (target) {
      case 'confirm': return changeImagingOrderStatus(pk, { status: 'scheduled' })
      case 'acquire': return changeImagingOrderStatus(pk, { status: 'acquired' })
      case 'cancel': return changeImagingOrderStatus(pk, { status: 'cancelled', reason: reason.trim() })
      case 'book': return bookScan(pk, slot)
      case 'cancelBooking': return cancelScanBooking(pk, reason.trim())
      case 'noShow': return markScanNoShow(pk)
      default: return remindPatient(pk)
    }
  }

  const confirm = async () => {
    const found = {}
    if (dialog.needsReason && !reason.trim()) found.reason = 'Write the reason.'
    if (target === 'book' && !slot) found.slot = 'Choose a scan slot.'
    setErrors(found)
    if (Object.keys(found).length) return
    setBusy(true)
    try {
      const result = await run()
      if (target !== 'remind') setData(result)
      setFlash(dialog.done)
      setTarget(null)
    } catch (err) {
      const { form, status, ...rest } = fieldErrors(err)
      setErrors({
        ...rest,
        form: form || status || (Object.keys(rest).length ? '' : getErrorMessage(err, 'Could not change the order.')),
      })
      reload() // someone else may have changed the order meanwhile
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader back={back} eyebrow={`Imaging order #${order.imaging_order_id}`}
        title={order.billing_service_name}
        actions={Object.values(actions).some(Boolean) && BUTTONS.filter(([action]) => actions[action]).map(
          ([action, label, variant]) => (
            <Button key={action} variant={variant} onClick={() => open(action)}>
              {action === 'book' && order.appointment ? 'Change slot' : label}
            </Button>
          ),
        )} />
      <div className="patient-summary">
        <Link className="patient-summary__mrn" to={`/patients/${order.patient}`}>{order.patient_name}</Link>
        <span className="muted-text">· {order.patient_mrn}</span>
        <ImagingStatusBadge status={order.status} />
      </div>

      <div className="content-stack">
        {flash && <Alert variant="success">{flash}</Alert>}
        {billingMessage && <Alert variant="error">{billingMessage}</Alert>}
        <div className="content-grid content-grid--even">
          <Panel title="Request">
            <dl className="detail-list">
              <div>
                <dt>Imaging Type</dt><dd>{order.billing_service_name} ({order.billing_service_code})</dd>
              </div>
              <div><dt>Clinical indication</dt><dd className="imaging-pre">{order.clinical_indication}</dd></div>
            </dl>
          </Panel>
          <Panel title="Order details">
            <dl className="detail-list">
              <div><dt>Ordered by</dt><dd>{order.ordered_by_name}</dd></div>
              <div><dt>Ordered on</dt><dd>{formatDateTime(order.order_date)}</dd></div>
              {order.status === 'acquired' && (
                <div>
                  <dt>Billing status</dt>
                  <dd>{order.billing_state === 'invoiced' ? 'Invoice created'
                    : order.billing_state === 'needs_service' ? 'Billing follow-up required'
                      : order.billing_state === 'needs_review' ? 'Billing review required' : 'Not ready'}</dd>
                </div>
              )}
              <div>
                <dt>Visit</dt>
                <dd>
                  {order.encounter
                    ? <Link to={`/encounters/${order.encounter}`}>{formatDateTime(order.encounter_date)}</Link>
                    : 'Not linked'}
                </dd>
              </div>
              <div>
                <dt>Scan appointment</dt>
                <dd>
                  {order.appointment
                    ? `${formatWhen(order.appointment_start)} (${APPOINTMENT_STATUS[order.appointment_status]?.label || order.appointment_status})`
                    : BOOKING_STATE.none}
                  {order.booking_state === 'pending' && ` · ${BOOKING_STATE.pending}`}
                </dd>
              </div>
            </dl>
          </Panel>
        </div>
      </div>

      <ConfirmDialog open={Boolean(target)} title={dialog.title} confirmLabel={dialog.confirm} busy={busy}
        tone={dialog.tone || 'primary'} onConfirm={confirm} onCancel={() => setTarget(null)}>
        <div className="form-stack">
          {errors.form && <Alert variant="error">{errors.form}</Alert>}
          {target === 'book' && (
            <ScanSlotPicker load={loadSlots} value={slot} error={errors.slot}
              onChange={(value) => { setSlot(value); setErrors({}) }} />
          )}
          {dialog.needsReason && (
            <TextAreaField label="Reason" name="reason" rows={3} maxLength={500} value={reason} error={errors.reason}
              onChange={(event) => setReason(event.target.value)} />
          )}
          <p>{dialog.text} The change is recorded in the audit log.</p>
        </div>
      </ConfirmDialog>
    </>
  )
}
