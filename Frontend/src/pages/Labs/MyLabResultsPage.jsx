import { useCallback } from 'react'
import { getErrorMessage } from '../../api/auth'
import { getMyTrend, listMyResults } from '../../api/labs'
import Alert from '../../components/ui/Alert'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { FlaskIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { flagBadge } from './labDisplay'
import { formatValue, rangeText } from './labFormat'
import ResultsTrendPanel from './ResultsTrendPanel'
import './Labs.css'

/** Patient portal: own lab results (only those released by the doctor) and their trends. */
export default function MyLabResultsPage() {
  const loader = useCallback(() => listMyResults({ page_size: 100 }), [])
  const { data, error, loading } = useApi(loader)

  return (
    <>
      <PageHeader eyebrow="Patient portal" title="My lab results" />
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load your lab results.')}</Alert>}
      {loading && !data ? (
        <LoadingBlock label="Loading your lab results" />
      ) : data ? (
        data.results.length ? (
          <div className="content-stack">
            <Panel title="Trend" subtitle="How a result has changed over time">
              <ResultsTrendPanel results={data.results} loadTrend={getMyTrend} />
            </Panel>
            <Panel title="Results" subtitle="Your doctor releases results after reviewing them" flush>
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th scope="col">Test</th>
                      <th scope="col">Result</th>
                      <th scope="col" className="hide-sm">Normal range</th>
                      <th scope="col">Flag</th>
                      <th scope="col" className="hide-sm">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.results.map((r) => (
                      <tr key={r.id}>
                        <td className="cell-primary">{r.test_name}</td>
                        <td>{formatValue(r.value)} {r.unit}</td>
                        <td className="hide-sm">{rangeText(r.normal_min, r.normal_max)} {r.unit}</td>
                        <td>{flagBadge(r.flag)}</td>
                        <td className="hide-sm">{formatDateTime(r.result_time)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
            <p className="muted-text panel-note">
              These values are for information. Please discuss them with your doctor before acting on them.
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
