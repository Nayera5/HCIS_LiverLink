import './ui.css'

/**
 * Simple horizontal bar chart (no chart library). Each bar shows its label and value as text,
 * so the chart is readable by screen readers and on phones.
 *
 * @param {{ label: string, value: number }[]} data
 * @param {(value: number) => string} formatValue  How to print a value (default: as is).
 * @param {string} title  Accessible name of the chart.
 */
export default function BarChart({ data = [], formatValue = String, title, emptyText = 'No data for this period.' }) {
  if (!data.length) return <p className="bar-chart__empty">{emptyText}</p>
  const max = Math.max(...data.map((point) => point.value), 0)

  return (
    <ul className="bar-chart" aria-label={title}>
      {data.map((point, index) => {
        const width = max > 0 ? Math.max((point.value / max) * 100, point.value > 0 ? 1.5 : 0) : 0
        return (
          <li key={`${point.label}-${index}`} className="bar-chart__row">
            <span className="bar-chart__label" title={point.label}>{point.label}</span>
            <span className="bar-chart__track" aria-hidden="true">
              <svg className="bar-chart__svg" viewBox="0 0 100 10" preserveAspectRatio="none" focusable="false">
                <rect className="bar-chart__bar" x="0" y="0" width={width} height="10" rx="1.5" />
              </svg>
            </span>
            <span className="bar-chart__value">{formatValue(point.value)}</span>
          </li>
        )
      })}
    </ul>
  )
}
