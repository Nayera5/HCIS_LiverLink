import { useCallback, useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { listMyLabOrders } from '../../api/labs'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import { EmptyState, LoadingBlock, Pagination } from '../../components/ui/Feedback'
import { FlaskIcon } from '../../components/ui/icons'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { priorityBadge } from './labDisplay'
import './Labs.css'

const PAGE_SIZE = 10

// Patient wording: no values here, only where each test stands.
const TEST_STATES = {
  pending: { tone: 'info', label: 'Waiting for the lab' },
  awaiting_review: { tone: 'warning', label: 'Being reviewed by your doctor' },
  available: { tone: 'success', label: 'Result available' },
}

function badge(map, key) {
  const info = map[key] || { tone: 'neutral', label: key }
  return <Badge tone={info.tone}>{info.label}</Badge>
}

/** Order summary in patient terms, derived from its tests (never "Completed" while still under review). */
function orderBadge(order) {
  if (order.status === 'cancelled') return <Badge>Cancelled</Badge>
  const states = order.tests.map((t) => t.state)
  if (states.every((s) => s === 'available')) return <Badge tone="success">Results available</Badge>
  if (states.includes('pending')) return <Badge tone="info">In progress</Badge>
  return <Badge tone="warning">Being reviewed</Badge>
}

/** "Orders" tab of the patient's lab page: the tests a doctor ordered and where each one stands. */
export default function MyLabOrders() {
  const [page, setPage] = useState(1)
  const loader = useCallback(() => listMyLabOrders({ page, page_size: PAGE_SIZE }), [page])
  const { data, error, loading } = useApi(loader)

  return (
    <>
      <div className="content-stack">
        <Alert variant="info">
          Values appear under Results after your doctor reviews and releases them.
        </Alert>
        {error && <Alert variant="error">{getErrorMessage(error, 'Could not load your lab orders.')}</Alert>}

        {loading && !data ? (
          <LoadingBlock label="Loading your lab orders" />
        ) : data?.results.length ? (
          <>
            {data.results.map((order) => (
              <Panel key={order.id} flush
                title={`Ordered ${formatDateTime(order.order_date)}`}
                subtitle={`By ${order.ordered_by_name}`}
                action={<div className="inline-actions">{order.priority === 'urgent' && priorityBadge('urgent')}{orderBadge(order)}</div>}>
                <div className="table-wrap">
                  <table className="data-table my-orders-table">
                    <thead>
                      <tr><th scope="col">Test</th><th scope="col">Status</th></tr>
                    </thead>
                    <tbody>
                      {order.tests.map((test) => (
                        <tr key={test.id}>
                          <td className="cell-primary">{test.test_name}</td>
                          <td>
                            {order.status === 'cancelled' && test.state !== 'available'
                              ? <Badge>Cancelled</Badge>
                              : badge(TEST_STATES, test.state)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            ))}
            <Pagination page={page} pageSize={PAGE_SIZE} count={data.count} onPageChange={setPage} />
          </>
        ) : (
          <Panel>
            <EmptyState icon={FlaskIcon} title="No lab orders yet">
              When your doctor orders lab tests for you, they appear here.
            </EmptyState>
          </Panel>
        )}
      </div>
    </>
  )
}
