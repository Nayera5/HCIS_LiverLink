import { useId, useState } from 'react'
import { ChevronDownIcon } from './icons'
import './ui.css'

/**
 * White card with a title row (design reference: "Today's appointments", "Clinical alerts").
 * @param {ReactNode} action  Right-aligned link/button in the header.
 * @param {boolean} flush     Body without padding (for tables).
 * @param {boolean} collapsible  Hide the body behind a toggle, initially closed.
 */
export default function Panel({
  title, subtitle, action, flush = false, divided = false, collapsible = false, className = '', children, ...rest
}) {
  const [open, setOpen] = useState(false)
  const bodyId = useId()

  return (
    <section className={`panel ${className}`} {...rest}>
      {(title || action) && (
        <header className={`panel__header ${divided ? 'panel__header--divided' : ''}`}>
          {collapsible ? (
            <button type="button" className="panel__toggle" aria-expanded={open} aria-controls={bodyId}
              onClick={() => setOpen((value) => !value)}>
              <span className="panel__toggle-text">
                {title && <span role="heading" aria-level="2" className="panel__title">{title}</span>}
                {subtitle && <span className="panel__subtitle">{subtitle}</span>}
              </span>
              <ChevronDownIcon className={`panel__chevron ${open ? 'panel__chevron--open' : ''}`} size={18} />
            </button>
          ) : (
            <div>
              {title && <h2 className="panel__title">{title}</h2>}
              {subtitle && <p className="panel__subtitle">{subtitle}</p>}
            </div>
          )}
          {action && <div className="panel__action">{action}</div>}
        </header>
      )}
      <div id={collapsible ? bodyId : undefined} hidden={collapsible && !open}
        className={`panel__body ${flush ? 'panel__body--flush' : ''}`}>
        {children}
      </div>
    </section>
  )
}
