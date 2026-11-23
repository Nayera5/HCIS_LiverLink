// Reporting & Analytics building blocks, shared by the Reports page, the dashboards and the
// medical-record pages (imaging & AI placeholders).
import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { getReport } from '../../api/reports'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import BarChart from '../../components/ui/BarChart'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { ClockIcon } from '../../components/ui/icons'
import Panel from '../../components/ui/Panel'
import StatCard from '../../components/ui/StatCard'
import { useApi } from '../../hooks/useApi'
import { chartData, formatCell, formatNumber, isMoneyColumn } from './reportDisplay'
import './Reports.css'

const SUMMARY_TONES = ['teal', 'info', 'warning', 'success', 'neutral']

/** KPI tiles from `report.summary`. */
export function SummaryTiles({ summary }) {
  return (
    <div className="stat-grid">
      {summary.map((item, index) => (
        <StatCard key={item.label} label={item.label} tone={SUMMARY_TONES[index % SUMMARY_TONES.length]}
          value={formatCell(item.label, item.value)} />
      ))}
    </div>
  )
}

/** One report section: a bar chart (when the section has a chart column) and its data table. */
export function ReportSectionPanel({ section }) {
  const points = chartData(section)
  const valueColumn = section.chart_column != null ? section.columns[section.chart_column] : ''
  const formatValue = (value) => formatCell(valueColumn, value)

  return (
    <Panel title={section.title} subtitle={`${section.rows.length} row${section.rows.length === 1 ? '' : 's'}`}
      className={`report-section ${section.columns.length > 4 ? 'report-section--wide' : ''}`} flush>
      {section.chart_column != null && (
        <div className="report-section__chart">
          <BarChart data={points} title={section.title} formatValue={formatValue} />
        </div>
      )}
      {section.rows.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                {section.columns.map((column) => (
                  <th key={column} scope="col" className={isMoneyColumn(column) ? 'cell-number' : ''}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {section.rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {row.map((value, index) => (
                    <td key={index} className={isMoneyColumn(section.columns[index]) || typeof value === 'number' ? 'cell-number' : ''}>
                      {formatCell(section.columns[index], value)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        section.chart_column == null && <EmptyState title="No data for this period" />
      )}
    </Panel>
  )
}

/** Placeholder for a report whose module (radiology, AI, transplant) is not built yet. */
export function ComingSoonPanel({ title, planned = [], children }) {
  return (
    <Panel title={title} action={<Badge tone="neutral">Coming soon</Badge>}>
      <EmptyState icon={ClockIcon} title="Not available yet">
        {children || 'This report becomes available once its module is added to LiverLink.'}
      </EmptyState>
      {planned.length > 0 && (
        <>
          <p className="report-planned__title">This report will show</p>
          <ul className="report-planned">
            {planned.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </>
      )}
    </Panel>
  )
}

/** Imaging & AI reports of one patient (hepatologist view or patient portal): placeholder for now. */
export function PatientImagingReportsPanel({ own = false }) {
  return (
    <ComingSoonPanel title={own ? 'My imaging & AI reports' : 'Imaging & AI reports'}
      planned={['CT studies and their dates', 'Signed radiology reports (LI-RADS)', 'AI liver and lesion measurements',
        'Liver and graft volumes (donors)']}>
      {own
        ? 'Your CT results and AI measurements will appear here once the imaging service is available.'
        : 'This patient’s CT studies, radiology reports and AI results will appear here once the Radiology and AI modules are available.'}
    </ComingSoonPanel>
  )
}

// --------------------------------------------------------------------------- dashboard highlights

// One chart per report the user may open; the dashboard shows the current year.
const HIGHLIGHTS = [
  { key: 'patients', capability: 'reports.patients', section: 'by_category', title: 'Patients by category' },
  { key: 'financial', capability: 'reports.financial', section: 'revenue_by_month', title: 'Revenue this year' },
  { key: 'system_usage', capability: 'reports.system_usage', section: 'appointments_by_status', title: 'Appointments this year' },
]

function HighlightPanel({ config }) {
  const loader = useCallback(
    () => getReport(config.key, { date_from: `${new Date().getFullYear()}-01-01` }),
    [config.key],
  )
  const { data, error, loading } = useApi(loader)
  const section = data?.sections.find((item) => item.key === config.section)
  const valueColumn = section ? section.columns[section.chart_column] : ''

  return (
    <Panel title={config.title} action={<Link to={`/reports?tab=${config.key}`}>Full report</Link>}>
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load this chart.')}</Alert>}
      {loading && !data ? (
        <LoadingBlock label="Loading chart" />
      ) : section ? (
        <BarChart data={chartData(section)} title={config.title}
          formatValue={(value) => (isMoneyColumn(valueColumn) ? formatCell(valueColumn, value) : formatNumber(value))} />
      ) : null}
    </Panel>
  )
}

/** Charts for the signed-in role on the dashboard (renders nothing without report access). */
export function ReportHighlights() {
  const { can } = useAuth()
  const items = HIGHLIGHTS.filter((item) => can(item.capability))
  if (!items.length) return null
  return (
    <div className="report-highlights">
      {items.map((item) => <HighlightPanel key={item.key} config={item} />)}
    </div>
  )
}
