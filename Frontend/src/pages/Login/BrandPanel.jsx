import LiverIllustration from './LiverIllustration'

const HIGHLIGHTS = [
  'AI-assisted CT analysis',
  'MELD · Milan · GRWR decision support',
  'Transplant case tracking',
]

export function BrandMark({ className = '' }) {
  return (
    <div className={`brand ${className}`}>
      <span className="brand__logo" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor"
          strokeWidth="2.4" strokeLinecap="round">
          <rect x="3.5" y="7.5" width="17" height="9" rx="4.5" transform="rotate(-35 12 12)" />
          <path d="M9.5 14.5 14.5 9.5" />
        </svg>
      </span>
      <span className="brand__text">
        <span className="brand__name">LiverLink</span>
        <span className="brand__tagline">Hepatology &amp; Transplant Center</span>
      </span>
    </div>
  )
}

export default function BrandPanel() {
  return (
    <aside className="brand-panel">
      <BrandMark />

      <div className="brand-panel__art">
        <LiverIllustration className="brand-panel__illustration" />
      </div>

      <div className="brand-panel__content">
        <h2 className="brand-panel__headline">
          Liver care and living-donor transplant, in one record.
        </h2>
        <p className="brand-panel__lead">
          From the first consultation and CT to committee decision, surgery and follow-up, the
          whole care team works from the same patient record.
        </p>
        <ul className="brand-panel__pills">
          {HIGHLIGHTS.map((item) => (
            <li key={item} className="pill">
              {item}
            </li>
          ))}
        </ul>
      </div>

      <footer className="brand-panel__footer">

      </footer>
    </aside>
  )
}
