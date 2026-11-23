import { useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import { ConfirmDialog } from '../../components/ui/Feedback'
import TextAreaField from '../../components/ui/TextAreaField'
import { formatDate } from '../../utils/format'
import { reviewState } from './rxFormat'

/** Review date with a badge when the review is overdue, today or within 14 days. */
export function ReviewDate({ plan }) {
  const state = reviewState(plan)
  return (
    <span className="rx-review">
      {formatDate(plan.review_date)}
      {state === 'overdue' && <Badge tone="danger">Review overdue</Badge>}
      {state === 'today' && <Badge tone="warning">Review today</Badge>}
      {state === 'soon' && <Badge tone="info">Review soon</Badge>}
    </span>
  )
}

/**
 * Confirmation dialog that asks for a reason. The reason is stored in the audit log.
 * onConfirm(reason) must return a promise; errors are shown inside the dialog.
 */
export function ReasonDialog({ open, title, children, confirmLabel, tone = 'primary', required = true, onConfirm, onCancel }) {
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const close = () => {
    setReason('')
    setError('')
    onCancel()
  }

  const confirm = async () => {
    if (required && !reason.trim()) {
      setError('Please give a reason. It is recorded in the audit log.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await onConfirm(reason.trim())
      setReason('')
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save. Please try again.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <ConfirmDialog open={open} title={title} confirmLabel={confirmLabel} tone={tone} busy={busy}
      onConfirm={confirm} onCancel={close}>
      <div className="form-stack">
        {children && <div>{children}</div>}
        {error && <Alert variant="error">{error}</Alert>}
        <TextAreaField label="Reason" optional={!required} value={reason} rows={3} maxLength={2000}
          onChange={(event) => setReason(event.target.value)} />
      </div>
    </ConfirmDialog>
  )
}
