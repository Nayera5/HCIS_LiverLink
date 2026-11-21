import './ui.css'

/** Small soft-coloured status label (design reference: Completed, No-show, Recipient, …). */
export default function Badge({ tone = 'neutral', children, className = '' }) {
  return <span className={`badge badge--${tone} ${className}`}>{children}</span>
}
