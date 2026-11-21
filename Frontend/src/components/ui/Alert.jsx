import { AlertCircleIcon, AlertTriangleIcon, CheckCircleIcon, ClockIcon } from './icons'
import './ui.css'

const DEFAULT_ICONS = {
  info: ClockIcon,
  error: AlertCircleIcon,
  success: CheckCircleIcon,
  warning: AlertTriangleIcon,
}

/**
 * Inline message box. Errors use role="alert" so screen readers announce them.
 * @param {'info'|'error'|'success'|'warning'} variant
 */
export default function Alert({ variant = 'info', icon, children, className = '' }) {
  const Icon = icon || DEFAULT_ICONS[variant]
  const role = variant === 'error' ? 'alert' : variant === 'success' ? 'status' : undefined

  return (
    <div className={`alert alert--${variant} ${className}`} role={role}>
      {Icon && <Icon className="alert__icon" />}
      <div className="alert__body">{children}</div>
    </div>
  )
}
