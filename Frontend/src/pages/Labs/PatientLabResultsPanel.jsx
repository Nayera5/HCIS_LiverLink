import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { getPatientTrend, listPatientResults } from '../../api/labs'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { FlaskIcon, PlusIcon } from '../../components/ui/icons'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { flagBadge } from './labDisplay'
import { formatValue, rangeText } from './labFormat'
import ResultsTrendPanel from './ResultsTrendPanel'
import './Labs.css'

/** Laboratory section of the patient profile (staff with labs.view): recent results + trend chart. */
export default function PatientLabResultsPanel({ patientId }) {
  const { can } = useAuth()
  const loader = useCallback(() => listPatientResults(patientId, { page_size: 100 }), [patientId])
  const { data, error, loading } = useApi(loader)
  const trendLoader = useCallback((code) => getPatientTrend(patientId, code), [patientId])

  const actions = (
    <div className="inline-actions">
      <Link to={`/lab/orders?patient=${patientId}`}>All orders</Link>
      {can('labs.order') && (
        <Button as={Link} size="sm" icon={PlusIcon} to={`/lab/orders/new?patient=${patientId}`}>Order tests</Button>
      )}
    </div>
  )

  return (
    <Panel title="Laboratory" subtitle="Results reported by the external lab" action={actions}>
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load lab results.')}</Alert>}
      {loading && !data ? (
        <LoadingBlock label="Loading lab results" />
      ) : data ? (
        data.results.length ? (
          <div className="content-stack">
            <ResultsTrendPanel results={data.results} loadTrend={trendLoader} />
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Test</th>
                    <th scope="col">Result</th>
                    <th scope="col" className="hide-sm">Normal range</th>
                    <th scope="col">Flag</th>
                    <th scope="col" className="hide-sm">Reported</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.slice(0, 10).map((r) => (
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
            {data.count > 10 && <p className="muted-text panel-note">Showing the 10 most recent of {data.count} results.</p>}
          </div>
        ) : (
          <EmptyState icon={FlaskIcon} title="No lab results yet">
            Results appear here once the lab reports them.
          </EmptyState>
        )
      ) : null}
    </Panel>
  )
}
