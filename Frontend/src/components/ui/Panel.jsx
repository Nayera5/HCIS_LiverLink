import './ui.css'

/**
 * White card with a title row (design reference: "Today's appointments", "Clinical alerts").
 * @param {ReactNode} action  Right-aligned link/button in the header.
 * @param {boolean} flush     Body without padding (for tables).
 */
export default function Panel({ title, subtitle, action, flush = false, divided = false, className = '', children, ...rest }) {
  return (
    <section className={`panel ${className}`} {...rest}>
      {(title || action) && (
        <header className={`panel__header ${divided ? 'panel__header--divided' : ''}`}>
          <div>
            {title && <h2 className="panel__title">{title}</h2>}
            {subtitle && <p className="panel__subtitle">{subtitle}</p>}
          </div>
          {action && <div className="panel__action">{action}</div>}
        </header>
      )}
      <div className={`panel__body ${flush ? 'panel__body--flush' : ''}`}>{children}</div>
    </section>
  )
}
