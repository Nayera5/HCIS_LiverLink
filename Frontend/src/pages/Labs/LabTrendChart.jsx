import { useState } from 'react'
import { formatDateTime } from '../../utils/format'
import { flagText } from './labDisplay'
import { formatValue, isAbnormal, niceTicks, rangeText, xPosition, yDomain } from './labFormat'

const W = 640
const H = 260
const M = { top: 16, right: 24, bottom: 34, left: 52 }
const PLOT_BOTTOM = H - M.bottom

const dateLabel = (value) =>
  new Date(value).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })

/**
 * Line chart of one lab value over time, with the normal range as a soft band.
 * Single series: no legend box (the heading names it). Every value is also in the table view below
 * and in the tooltip (hover or keyboard focus).
 */
export default function LabTrendChart({ points, testName, unit, normalMin, normalMax }) {
  const [active, setActive] = useState(null)

  if (!points.length) return null

  const data = points.map((p) => ({ ...p, time: new Date(p.date).getTime(), number: Number(p.value) }))
  const first = data[0].time
  const last = data[data.length - 1].time
  const [lo, hi] = yDomain(data.map((d) => d.number), normalMin, normalMax)
  const x = (time) => xPosition(time, first, last, M.left, W - M.right)
  const y = (value) => PLOT_BOTTOM - ((value - lo) / (hi - lo)) * (PLOT_BOTTOM - M.top)
  const yTicks = niceTicks(lo, hi)

  const bandTop = normalMax !== null && normalMax !== undefined ? y(Number(normalMax)) : M.top
  const bandBottom = normalMin !== null && normalMin !== undefined ? y(Number(normalMin)) : PLOT_BOTTOM
  const hasBand = (normalMin ?? null) !== null || (normalMax ?? null) !== null
  const path = data.map((d, i) => `${i ? 'L' : 'M'}${x(d.time).toFixed(1)} ${y(d.number).toFixed(1)}`).join(' ')

  // Show at most ~5 date labels so they never collide.
  const labelEvery = Math.max(1, Math.ceil(data.length / 5))

  const current = active === null ? null : data[active]
  const summary = `${testName}: ${data.length} result${data.length === 1 ? '' : 's'}, from ${formatValue(data[0].number)} to ${formatValue(data[data.length - 1].number)} ${unit || ''}.`

  const nearest = (event) => {
    const box = event.currentTarget.getBoundingClientRect()
    const px = ((event.clientX - box.left) / box.width) * W
    let best = 0
    data.forEach((d, i) => {
      if (Math.abs(x(d.time) - px) < Math.abs(x(data[best].time) - px)) best = i
    })
    setActive(best)
  }

  return (
    <figure className="lab-chart">
      <div className="lab-chart__plot" onPointerLeave={() => setActive(null)}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={summary}>
          {hasBand && (
            <rect className="lab-chart__band" x={M.left} y={bandTop} width={W - M.left - M.right}
              height={Math.max(0, bandBottom - bandTop)} />
          )}
          {yTicks.map((tick) => (
            <g key={tick}>
              <line className="lab-chart__grid" x1={M.left} x2={W - M.right} y1={y(tick)} y2={y(tick)} />
              <text className="lab-chart__tick" x={M.left - 8} y={y(tick)} textAnchor="end" dominantBaseline="middle">
                {formatValue(tick)}
              </text>
            </g>
          ))}
          {data.map((d, i) => (
            i % labelEvery === 0 && (
              <text key={d.date} className="lab-chart__tick" x={x(d.time)} y={H - 10} textAnchor="middle">
                {dateLabel(d.date)}
              </text>
            )
          ))}

          {current && (
            <line className="lab-chart__crosshair" x1={x(current.time)} x2={x(current.time)} y1={M.top}
              y2={PLOT_BOTTOM} />
          )}
          <path className="lab-chart__line" d={path} />

          {data.map((d, i) => (
            <g key={d.date + i} tabIndex={0} role="img"
              aria-label={`${formatDateTime(d.date)}: ${formatValue(d.number)} ${unit || ''} ${flagText(d.flag)}`}
              onFocus={() => setActive(i)} onBlur={() => setActive(null)}>
              <circle className={`lab-chart__dot ${isAbnormal(d.flag) ? 'lab-chart__dot--abnormal' : ''}`}
                cx={x(d.time)} cy={y(d.number)} r={d.flag === 'critical' ? 6 : 4.5} />
            </g>
          ))}

          {/* Pointer layer: snaps to the nearest date, so the reader never has to hit a 2px line. */}
          <rect className="lab-chart__hit" x={M.left} y={M.top} width={W - M.left - M.right}
            height={PLOT_BOTTOM - M.top} onPointerMove={nearest} onPointerDown={nearest} />
        </svg>

        {current && (
          <div className="lab-tooltip" role="status"
            style={{ left: `${(x(current.time) / W) * 100}%`, top: `${(y(current.number) / H) * 100}%` }}>
            <strong>{formatValue(current.number)} {unit}</strong>
            <span>{formatDateTime(current.date)}</span>
            <span>{flagText(current.flag) || 'Normal'}</span>
          </div>
        )}
      </div>
      <figcaption className="lab-chart__legend">
        <span><i className="lab-chart__key lab-chart__key--line" /> {testName}{unit ? ` (${unit})` : ''}</span>
        {hasBand && <span><i className="lab-chart__key lab-chart__key--band" /> Normal range {rangeText(normalMin, normalMax)}</span>}
        <span><i className="lab-chart__key lab-chart__key--abnormal" /> Outside normal range</span>
      </figcaption>

      <details className="lab-chart__table">
        <summary>View as table</summary>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th scope="col">Date</th><th scope="col">Value</th><th scope="col">Flag</th></tr>
            </thead>
            <tbody>
              {data.map((d, i) => (
                <tr key={d.date + i}>
                  <td>{formatDateTime(d.date)}</td>
                  <td>{formatValue(d.number)} {unit}</td>
                  <td>{flagText(d.flag) || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  )
}
