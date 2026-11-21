import { Link } from 'react-router-dom'
import './ui.css'

/**
 * KPI tile (design reference: "Today's appointments 12 …").
 * @param {'teal'|'success'|'danger'|'warning'|'info'|'neutral'} tone  Colour of the status dot.
 * @param {string} to  Optional link target; the whole card becomes clickable.
 */
export default function StatCard({ label, value, hint, tone = 'teal', to }) {
  const content = (
    <>
      <span className={`stat-card__dot stat-card__dot--${tone}`} aria-hidden="true" />
      <span className="stat-card__label">{label}</span>
      <span className="stat-card__value">{value ?? '–'}</span>
      {hint && <span className="stat-card__hint">{hint}</span>}
    </>
  )
  return to ? (
    <Link to={to} className="stat-card">
      {content}
    </Link>
  ) : (
    <div className="stat-card">{content}</div>
  )
}
