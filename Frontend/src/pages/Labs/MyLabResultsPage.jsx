import { useCallback, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { getMyTrend, listMyResults } from '../../api/labs'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { AlertTriangleIcon, CheckCircleIcon, FlaskIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDate } from '../../utils/format'
import { formatValue, isAbnormal, latestPerTest, plainFlag, rangeText } from './labFormat'
import MyLabOrders from './MyLabOrders'
import ResultsTrendPanel from './ResultsTrendPanel'
import '../Reports/Reports.css' // tab styles
import './Labs.css'

const PAGE_SIZE = 100

const TABS = [
  { key: 'results', label: 'Results' },
  { key: 'orders', label: 'Orders' },
]

/** Patient portal: own lab results and lab orders, as two tabs (the tab is kept in the URL). */
export default function MyLabResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') === 'orders' ? 'orders' : 'results'

  return (
    <>
      <PageHeader eyebrow="Patient portal" title="Lab & test results" />
      <div className="report-tabs" role="tablist" aria-label="Lab and test results">
        {TABS.map(({ key, label }) => (
          <button key={key} type="button" role="tab" aria-selected={key === tab}
            className={`report-tabs__tab ${key === tab ? 'report-tabs__tab--active' : ''}`}
            onClick={() => setSearchParams(key === 'orders' ? { tab: key } : {})}>
            {label}
          </button>
        ))}
      </div>
      {tab === 'orders' ? <MyLabOrders /> : <MyLabResults />}
    </>
  )
}

/**
 * Only results released by the doctor. Answers "am I OK?" first: a summary, then the latest result
 * of each test in plain words. The chart is optional, at the end.
 */
function MyLabResults() {
  const loader = useCallback(() => listMyResults({ page_size: PAGE_SIZE }), [])
  const { data, error, loading } = useApi(loader)
  const latest = data ? latestPerTest(data.results) : []

  return (
    <>
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load your lab results.')}</Alert>}
      {loading && !data ? (
        <LoadingBlock label="Loading your lab results" />
      ) : data ? (
        latest.length ? (
          <div className="content-stack">
            <Summary latest={latest} />
            <Panel title="Latest results" subtitle="The most recent result of each test" flush>
              <ul className="my-results">
                {latest.map((result) => <ResultRow key={result.id} result={result} />)}
              </ul>
            </Panel>
            <History results={data.results} />
            <p className="muted-text panel-note">
              Your doctor releases results after reviewing them. These values are for information. Please discuss
              them with your doctor before acting on them.
              {data.count > PAGE_SIZE && ` This page uses your ${PAGE_SIZE} most recent results.`}
            </p>
          </div>
        ) : (
          <Panel>
            <EmptyState icon={FlaskIcon} title="No lab results yet">
              Results appear here after the lab reports them and your doctor releases them.
            </EmptyState>
          </Panel>
        )
      ) : null}
    </>
  )
}

function Summary({ latest }) {
  if (latest.some((r) => r.flag === 'critical')) return null

  const abnormal = latest.filter((r) => isAbnormal(r.flag))
  const names = (list) => list.map((r) => r.test_name).join(', ')

  let tone = 'normal'
  let title = 'Your latest results are within the normal range'
  let text = ''
  if (abnormal.length) {
    tone = 'attention'
    title = abnormal.length === 1 ? '1 result is outside the normal range' : `${abnormal.length} results are outside the normal range`
    text = `${names(abnormal)}. Please discuss this with your doctor.`
  }

  const Icon = tone === 'normal' ? CheckCircleIcon : AlertTriangleIcon
  return (
    <section className={`my-results__summary my-results__summary--${tone}`}>
      <Icon size={24} />
      <div>
        <h2>{title}</h2>
        {text && <p>{text}</p>}
      </div>
    </section>
  )
}

const TONES = { critical: 'critical', high: 'warning', low: 'warning', normal: 'success' }

function ResultRow({ result }) {
  const range = rangeText(result.normal_min, result.normal_max)
  const { previous } = result
  return (
    <li className={`my-result my-result--${result.flag}`}>
      <div>
        <div className="cell-primary">{result.test_name}</div>
        <div className="cell-secondary">{formatDate(result.result_time)}</div>
      </div>
      <div>
        <div className="my-result__value">{formatValue(result.value)} <span>{result.unit}</span></div>
        {range !== '—' && <div className="cell-secondary">Normal: {range} {result.unit}</div>}
        {previous && (
          <div className="cell-secondary">
            Before: {formatValue(previous.value)} {previous.unit} ({formatDate(previous.result_time)})
          </div>
        )}
      </div>
      {result.flag && <Badge tone={TONES[result.flag]}>{plainFlag(result)}</Badge>}
    </li>
  )
}

/** Charts for those who want them: closed at first, and loaded only when opened. */
function History({ results }) {
  const [open, setOpen] = useState(false)
  return (
    <Panel flush>
      <details className="my-results__history" onToggle={(event) => setOpen(event.currentTarget.open)}>
        <summary>See how my results changed over time</summary>
        <div className="my-results__history-body">
          {open && <ResultsTrendPanel results={results} loadTrend={getMyTrend} />}
        </div>
      </details>
    </Panel>
  )
}
