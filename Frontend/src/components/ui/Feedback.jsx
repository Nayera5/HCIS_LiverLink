import { useEffect, useRef } from 'react'
import Button from './Button'
import './ui.css'

export function Spinner({ label = 'Loading' }) {
  return <span className="spinner" role="status" aria-label={label} />
}

export function LoadingBlock({ label }) {
  return (
    <div className="loading-block">
      <Spinner label={label} />
    </div>
  )
}

export function EmptyState({ icon: Icon, title, children }) {
  return (
    <div className="empty-state">
      {Icon && (
        <span className="empty-state__icon" aria-hidden="true">
          <Icon size={20} />
        </span>
      )}
      {title && <p className="empty-state__title">{title}</p>}
      {children && <div className="empty-state__text">{children}</div>}
    </div>
  )
}

export function Pagination({ page, pageSize, count, onPageChange }) {
  const pages = Math.max(1, Math.ceil(count / pageSize))
  if (count <= pageSize) return null
  const from = (page - 1) * pageSize + 1
  const to = Math.min(count, page * pageSize)
  return (
    <nav className="pagination" aria-label="Pagination">
      <span>
        {from}–{to} of {count}
      </span>
      <div className="pagination__buttons">
        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          Previous
        </Button>
        <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => onPageChange(page + 1)}>
          Next
        </Button>
      </div>
    </nav>
  )
}

/** Modal confirmation built on the native <dialog> (focus trapping and Esc handled by the browser). */
export function ConfirmDialog({ open, title, children, confirmLabel = 'Confirm', tone = 'primary', busy, onConfirm, onCancel }) {
  const ref = useRef(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      className="dialog"
      aria-labelledby="dialog-title"
      onCancel={(event) => {
        event.preventDefault()
        if (!busy) onCancel()
      }}
    >
      <div className="dialog__body">
        <h2 id="dialog-title" className="dialog__title">
          {title}
        </h2>
        <div className="dialog__text">{children}</div>
      </div>
      <div className="dialog__actions">
        <Button variant="secondary" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
        <Button variant={tone} onClick={onConfirm} loading={busy}>
          {confirmLabel}
        </Button>
      </div>
    </dialog>
  )
}
