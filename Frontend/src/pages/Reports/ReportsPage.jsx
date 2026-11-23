import { useCallback, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { exportReport, getReport } from '../../api/reports'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { LoadingBlock } from '../../components/ui/Feedback'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { ComingSoonPanel, ReportSectionPanel, SummaryTiles } from './reportPanels'
import { periodLabel, pickTab, tabsFor, validatePeriod } from './reportDisplay'
import '../Users/Users.css'
import './Reports.css'

/** Report data for one available tab, with the current date filter. */
function ReportView({ reportKey, period }) {
  const loader = useCallback(() => getReport(reportKey, period), [reportKey, period])
  const { data, error, loading } = useApi(loader)

  if (error) return <Alert variant="error">{getErrorMessage(error, 'Could not load this report.')}</Alert>
  if (loading && !data) return <LoadingBlock label="Loading report" />
  if (!data) return null
  return (
    <div aria-busy={loading}>
      <SummaryTiles summary={data.summary} />
      <div className="report-sections">
        {data.sections.map((section) => <ReportSectionPanel key={section.key} section={section} />)}
      </div>
    </div>
  )
}

/**
 * Reporting & Analytics (module 15). One tab per report the user may open; transplant and
 * imaging/AI tabs are placeholders until those modules exist. Filters live in the URL.
 */
export default function ReportsPage() {
  const { can } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const tabs = tabsFor(can)
  const tab = pickTab(tabs, searchParams.get('tab'))

  const dateFrom = searchParams.get('date_from') || ''
  const dateTo = searchParams.get('date_to') || ''
  const [draft, setDraft] = useState({ date_from: dateFrom, date_to: dateTo })
  const [errors, setErrors] = useState({})
  const [exporting, setExporting] = useState('')
  const [exportError, setExportError] = useState(null)

  // Memoised so the report loader only changes when the applied filter changes.
  const period = useMemo(() => ({ date_from: dateFrom, date_to: dateTo }), [dateFrom, dateTo])

  const update = (changes) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)))
    setSearchParams(next)
  }

  const applyFilter = (event) => {
    event.preventDefault()
    const found = validatePeriod(draft)
    setErrors(found)
    if (Object.keys(found).length === 0) update(draft)
  }

  const clearFilter = () => {
    setDraft({ date_from: '', date_to: '' })
    setErrors({})
    update({ date_from: '', date_to: '' })
  }

  const download = async (format) => {
    setExporting(format)
    setExportError(null)
    try {
      await exportReport(tab.key, format, period)
    } catch (error) {
      setExportError(getErrorMessage(error, 'Could not export this report.'))
    } finally {
      setExporting('')
    }
  }

  if (!tab) return null // the route guard only lets users with a report capability in

  return (
    <>
      <PageHeader eyebrow="Reporting & analytics" title="Reports"
        actions={tab.available && (
          <>
            <Button variant="secondary" loading={exporting === 'csv'} disabled={Boolean(exporting)}
              onClick={() => download('csv')}>Export CSV</Button>
            <Button variant="secondary" loading={exporting === 'pdf'} disabled={Boolean(exporting)}
              onClick={() => download('pdf')}>Export PDF</Button>
          </>
        )} />

      <div className="report-tabs" role="tablist" aria-label="Reports">
        {tabs.map((item) => (
          <button key={item.key} type="button" role="tab" aria-selected={item.key === tab.key}
            className={`report-tabs__tab ${item.key === tab.key ? 'report-tabs__tab--active' : ''}`}
            onClick={() => update({ tab: item.key })}>
            {item.label}
            {!item.available && <span className="report-tabs__soon">Soon</span>}
          </button>
        ))}
      </div>

      {exportError && <Alert variant="error" className="form-alert">{exportError}</Alert>}

      {tab.available ? (
        <>
          <Panel flush className="report-filter">
            <form className="filter-bar report-filter__form" onSubmit={applyFilter} noValidate>
              <TextField label="From" type="date" name="date_from" value={draft.date_from} error={errors.date_from}
                onChange={(event) => setDraft((prev) => ({ ...prev, date_from: event.target.value }))} />
              <TextField label="To" type="date" name="date_to" value={draft.date_to} error={errors.date_to}
                onChange={(event) => setDraft((prev) => ({ ...prev, date_to: event.target.value }))} />
              <Button type="submit">Apply</Button>
              {(dateFrom || dateTo) && (
                <Button variant="link" className="filter-bar__clear" onClick={clearFilter}>Show all time</Button>
              )}
            </form>
            <p className="report-filter__period">Showing: <strong>{periodLabel(period)}</strong></p>
          </Panel>
          <ReportView reportKey={tab.key} period={period} />
        </>
      ) : (
        <ComingSoonPanel title={`${tab.label} reports`} planned={tab.planned} />
      )}
    </>
  )
}

