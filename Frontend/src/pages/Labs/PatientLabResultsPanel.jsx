import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { getPatientTrend, listLabOrders, listPatientResults } from '../../api/labs'
import { loadAllPages } from '../../api/pagination'
import Alert from '../../components/ui/Alert'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { FlaskIcon } from '../../components/ui/icons'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { flagBadge, priorityBadge, statusBadge } from './labDisplay'
import { formatValue, rangeText } from './labFormat'
import ResultsTrendPanel from './ResultsTrendPanel'
import './Labs.css'

/** Laboratory section of the medical record: orders, reported results and trends. */
export default function PatientLabResultsPanel({ patientId }) {
  const loader = useCallback(async () => {
    const [results, orders] = await Promise.all([
      loadAllPages((params) => listPatientResults(patientId, params)),
      loadAllPages(listLabOrders, { patient: patientId }),
    ])
    return { results, orders }
  }, [patientId])
  const { data, error, loading } = useApi(loader)
  const trendLoader = useCallback((code) => getPatientTrend(patientId, code), [patientId])

  const actions = (
    <Link to={`/lab/orders?patient=${patientId}`}>All orders</Link>
  )

  return (
    <Panel title="Laboratory" subtitle="Orders, requested tests and reported results" action={actions} collapsible>
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load lab results.')}</Alert>}
      {loading && !data ? (
        <LoadingBlock label="Loading lab results" />
      ) : data ? (
        data.orders.length || data.results.length ? (
          <div className="content-stack">
            <section className="content-stack">
              <h3>Lab orders and tests</h3>
              {data.orders.length ? (
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th scope="col">Ordered</th>
                        <th scope="col">Tests</th>
                        <th scope="col">Encounter</th>
                        <th scope="col">Priority</th>
                        <th scope="col">Status</th>
                        <th scope="col"><span className="visually-hidden">Actions</span></th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.orders.map((order) => {
                        const done = order.results.filter((result) => !result.is_pending).length
                        return (
                          <tr key={order.id}>
                            <td>{formatDateTime(order.order_date)}</td>
                            <td>
                              <div>{order.results.map((result) => result.test_name).join(', ')}</div>
                              <div className="cell-secondary">{done} of {order.results.length} resulted</div>
                            </td>
                            <td>
                              {order.encounter
                                ? <Link to={`/encounters/${order.encounter}`}>Visit #{order.encounter}</Link>
                                : '—'}
                            </td>
                            <td>{priorityBadge(order.priority)}</td>
                            <td>{statusBadge(order.status)}</td>
                            <td className="cell-actions"><Link to={`/lab/orders/${order.id}`}>Open order</Link></td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              ) : <p className="muted-text">No lab orders yet.</p>}
            </section>
            {data.results.length > 0 && (
              <>
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
              </>
            )}
          </div>
        ) : (
          <EmptyState icon={FlaskIcon} title="No lab orders yet">
            Lab orders created during encounters appear here.
          </EmptyState>
        )
      ) : null}
    </Panel>
  )
}
