import { useCallback, useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import { bookMyScan, cancelMyScan, listMyImagingOrders, listMyOrderSlots } from '../../api/imaging'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { ConfirmDialog, EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { ScanIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { formatWhen } from '../Appointments/appointmentRules'
import { BookingText, ImagingStatusBadge, ScanSlotPicker } from '../Imaging/imagingParts'
import { patientScanActions } from '../Imaging/imagingRules'

function ChooseSlotDialog({ order, onDone, onCancel }) {
  const [slot, setSlot] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const load = useCallback((params) => listMyOrderSlots(order.imaging_order_id, params), [order.imaging_order_id])

  const save = async () => {
    if (!slot) {
      setError('Choose a scan slot.')
      return
    }
    setBusy(true)
    try {
      onDone(await bookMyScan(order.imaging_order_id, slot))
    } catch (err) {
      const found = fieldErrors(err)
      setError(found.slot || found.form || getErrorMessage(err, 'Could not book the scan.'))
      setBusy(false)
    }
  }

  return (
    <ConfirmDialog open title={order.appointment ? 'Change scan appointment' : 'Choose a scan appointment'}
      confirmLabel="Choose this slot" busy={busy} onConfirm={save} onCancel={onCancel}>
      <div className="form-stack">
        <p>
          {order.billing_service_name}.
          {order.appointment ? ` Now: ${formatWhen(order.appointment_start)}.` : ''} The radiology department
          confirms the time you choose.
        </p>
        <ScanSlotPicker load={load} value={slot} error={error}
          onChange={(value) => { setSlot(value); setError('') }} />
      </div>
    </ConfirmDialog>
  )
}

/** Portal: own scan requests (self.imaging_orders). No doctor is chosen: only a scan slot. */
export default function MyImagingPage() {
  const { data, error, loading, reload, setData } = useApi(listMyImagingOrders)
  const [dialog, setDialog] = useState(null) // { type: 'choose' | 'cancel', order }
  const [flash, setFlash] = useState('')
  const [actionError, setActionError] = useState('')
  const [busy, setBusy] = useState(false)

  const open = (type, order) => {
    setDialog({ type, order })
    setFlash('')
    setActionError('')
  }
  const close = () => {
    setDialog(null)
    reload() // the order may have changed meanwhile
  }
  const update = (order, message) => {
    setData(data.map((row) => (row.imaging_order_id === order.imaging_order_id ? order : row)))
    setFlash(message)
    setDialog(null)
  }

  const cancel = async () => {
    setBusy(true)
    try {
      update(await cancelMyScan(dialog.order.imaging_order_id),
        'Scan appointment cancelled. You can choose another one.')
    } catch (err) {
      setActionError(fieldErrors(err).form || getErrorMessage(err, 'Could not cancel the scan appointment.'))
      close()
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader eyebrow="Patient portal" title="My scans" />
      <div className="content-stack">
        {flash && <Alert variant="success">{flash}</Alert>}
        {actionError && <Alert variant="error">{actionError}</Alert>}
        {error && <Alert variant="error">{getErrorMessage(error, 'Could not load your scans.')}</Alert>}
        {loading && !data ? <LoadingBlock label="Loading scans" /> : data && (
          <Panel title="Scan requests" flush={data.length > 0}>
            {data.length ? (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th scope="col">Examination</th>
                      <th scope="col">Status</th>
                      <th scope="col">Scan appointment</th>
                      <th scope="col" className="hide-sm">Requested</th>
                      <th scope="col"><span className="visually-hidden">Actions</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((order) => {
                      const actions = patientScanActions(order)
                      return (
                        <tr key={order.imaging_order_id}>
                          <td className="cell-primary">{order.billing_service_name}</td>
                          <td><ImagingStatusBadge status={order.status} /></td>
                          <td><BookingText order={order} /></td>
                          <td className="hide-sm">{formatDateTime(order.order_date)}</td>
                          <td className="cell-actions">
                            <div className="appt-actions">
                              {actions.choose && (
                                <Button size="sm" variant={order.appointment ? 'secondary' : 'primary'}
                                  onClick={() => open('choose', order)}>
                                  {order.appointment ? 'Change time' : 'Choose appointment'}
                                </Button>
                              )}
                              {actions.cancel && (
                                <Button size="sm" variant="secondary" onClick={() => open('cancel', order)}>
                                  Cancel appointment
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState icon={ScanIcon} title="No scan requests">
                When your doctor requests a scan, you can choose its appointment here.
              </EmptyState>
            )}
          </Panel>
        )}
      </div>
      {dialog?.type === 'choose' && (
        <ChooseSlotDialog order={dialog.order} onCancel={close}
          onDone={(order) => update(order,
            `Scan slot chosen: ${formatWhen(order.appointment_start)}. Waiting for confirmation.`)} />
      )}
      {dialog?.type === 'cancel' && (
        <ConfirmDialog open title="Cancel scan appointment?" confirmLabel="Cancel appointment" tone="danger"
          busy={busy} onConfirm={cancel} onCancel={() => setDialog(null)}>
          {formatWhen(dialog.order.appointment_start)}. Your scan request stays open: please choose another time.
        </ConfirmDialog>
      )}
    </>
  )
}
