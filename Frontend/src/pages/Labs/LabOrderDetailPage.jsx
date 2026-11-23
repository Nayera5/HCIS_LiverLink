import { useCallback, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { cancelLabOrder, getLabOrder, releaseLabOrder } from '../../api/labs'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { ConfirmDialog, LoadingBlock } from '../../components/ui/Feedback'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { flagBadge, priorityBadge, statusBadge } from './labDisplay'
import { formatValue, rangeText } from './labFormat'
import ResultEntryForm from './ResultEntryForm'
import './Labs.css'

export default function LabOrderDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const { can } = useAuth()
  const loader = useCallback(() => getLabOrder(id), [id])
  const { data: order, error, loading, setData, reload } = useApi(loader)
  const [flash, setFlash] = useState(location.state?.flash || '')
  const [problem, setProblem] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [confirmCancel, setConfirmCancel] = useState(false)
  const [busy, setBusy] = useState(false)

  if (loading && !order) return <LoadingBlock label="Loading lab order" />
  if (error && !order) {
    return (
      <>
        <PageHeader back={{ to: '/lab/orders', label: 'Lab orders' }} title="Lab order" />
        <Alert variant="error">{getErrorMessage(error, 'Could not load this lab order.')}</Alert>
      </>
    )
  }

  const cancelled = order.status === 'cancelled'
  const resulted = order.results.filter((r) => !r.is_pending)
  const canRelease = can('labs.release') && !cancelled && resulted.some((r) => !r.is_released)
  const canCancel = can('labs.order') && (order.status === 'ordered' || order.status === 'partially_resulted')
  const canEnter = can('labs.enter_result') && !cancelled

  const run = async (action, successMessage, failMessage) => {
    setBusy(true)
    setProblem('')
    try {
      setData(await action())
      setFlash(successMessage)
    } catch (err) {
      setProblem(getErrorMessage(err, failMessage))
    } finally {
      setBusy(false)
      setConfirmCancel(false)
    }
  }

  const saved = (result) => {
    setEditingId(null)
    setFlash('Result saved. The abnormal flag was set from the normal range.')
    // Show the saved row at once, then refetch: the order status changes when the last test is resulted.
    setData({ ...order, results: order.results.map((r) => (r.id === result.id ? result : r)) })
    reload()
  }

  return (
    <>
      <PageHeader
        back={{ to: '/lab/orders', label: 'Lab orders' }}
        eyebrow="Lab order"
        title={`Order #${order.id}`}
        actions={(
          <>
            {canRelease && (
              <Button loading={busy} onClick={() => run(() => releaseLabOrder(order.id),
                'Results released: the patient can now see them in the portal.', 'Could not release the results.')}>
                Release to patient
              </Button>
            )}
            {canCancel && <Button variant="danger" onClick={() => setConfirmCancel(true)}>Cancel order</Button>}
          </>
        )}
      />
      <div className="patient-summary">
        <Link className="patient-summary__mrn" to={`/patients/${order.patient}`}>{order.patient_name}</Link>
        <span className="muted-text">· {order.patient_mrn}</span>
        {statusBadge(order.status)}
        {priorityBadge(order.priority)}
      </div>

      <div className="content-stack">
        {flash && <Alert variant="success">{flash}</Alert>}
        {problem && <Alert variant="error">{problem}</Alert>}
        {cancelled && <Alert variant="warning">This order was cancelled. No more results can be entered.</Alert>}

        <Panel title="Tests" subtitle={`Ordered ${formatDateTime(order.order_date)} by ${order.ordered_by_name}`} flush>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Test</th>
                  <th scope="col">Result</th>
                  <th scope="col" className="hide-sm">Normal range</th>
                  <th scope="col">Flag</th>
                  <th scope="col" className="hide-sm">Reported</th>
                  <th scope="col"><span className="visually-hidden">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {order.results.map((result) => (
                  <tr key={result.id}>
                    <td className="cell-primary">{result.test_name}</td>
                    <td>
                      {editingId === result.id ? (
                        <ResultEntryForm result={result} onSaved={saved} onCancel={() => setEditingId(null)} />
                      ) : result.is_pending ? (
                        <Badge tone="info">Pending</Badge>
                      ) : (
                        <>
                          {formatValue(result.value)} {result.unit}
                          {result.is_released && <div className="cell-secondary">Visible to patient</div>}
                        </>
                      )}
                    </td>
                    <td className="hide-sm">{rangeText(result.normal_min, result.normal_max)} {result.unit}</td>
                    <td>{flagBadge(result.flag)}</td>
                    <td className="hide-sm">{formatDateTime(result.result_time)}</td>
                    <td className="cell-actions">
                      {canEnter && editingId !== result.id && (
                        <Button variant="link" onClick={() => { setEditingId(result.id); setFlash('') }}>
                          {result.is_pending ? 'Enter result' : 'Correct'}
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      <ConfirmDialog open={confirmCancel} title="Cancel this lab order?" confirmLabel="Cancel order" tone="danger"
        busy={busy} onCancel={() => setConfirmCancel(false)}
        onConfirm={() => run(() => cancelLabOrder(order.id), 'Order cancelled.', 'Could not cancel the order.')}>
        Pending tests will no longer be expected from the lab. This is recorded in the audit log.
      </ConfirmDialog>
    </>
  )
}
