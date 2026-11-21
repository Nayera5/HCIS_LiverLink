import { useCallback, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { listPendingTests } from '../../api/labs'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock, Pagination } from '../../components/ui/Feedback'
import { FlaskIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import Badge from '../../components/ui/Badge'
import { PRIORITY_OPTIONS, priorityBadge } from './labDisplay'
import { formatValue } from './labFormat'
import ResultEntryForm from './ResultEntryForm'
import '../Users/Users.css'
import './Labs.css'

const PAGE_SIZE = 20

/** Tests ordered but not yet reported by the external lab, urgent first. */
export default function PendingTestsPage() {
  const { can } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const priority = searchParams.get('priority') || ''
  const page = Number(searchParams.get('page')) || 1
  const [flash, setFlash] = useState('')
  const [editingId, setEditingId] = useState(null)

  const query = searchParams.toString()
  const loader = useCallback(
    () => listPendingTests({ ...Object.fromEntries(new URLSearchParams(query)), page_size: PAGE_SIZE }),
    [query],
  )
  const { data, error, loading, reload } = useApi(loader)

  const update = (changes) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)))
    if (!('page' in changes)) next.delete('page')
    setSearchParams(next)
  }
  const canEnter = can('labs.enter_result')

  const saved = (result) => {
    setEditingId(null)
    setFlash(`${result.test_name}: ${formatValue(result.value)} ${result.unit} saved.`)
    reload()
  }

  return (
    <>
      <PageHeader eyebrow="Laboratory" title="Pending tests" />
      <Panel flush>
        <div className="filter-bar filter-bar--labs">
          <SelectField label="Priority" placeholder="Any" options={PRIORITY_OPTIONS} value={priority}
            onChange={(event) => update({ priority: event.target.value })} />
          {priority && (
            <Button variant="link" className="filter-bar__clear" onClick={() => update({ priority: '' })}>
              Clear filter
            </Button>
          )}
        </div>
        {flash && <div className="panel-inset"><Alert variant="success">{flash}</Alert></div>}
        {error && (
          <div className="panel-inset">
            <Alert variant="error">{getErrorMessage(error, 'Could not load pending tests.')}</Alert>
          </div>
        )}

        {loading && !data ? (
          <LoadingBlock label="Loading pending tests" />
        ) : data?.results.length ? (
          <>
            <div className="table-wrap" aria-busy={loading}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Patient</th>
                    <th scope="col">Test</th>
                    <th scope="col">Priority</th>
                    <th scope="col" className="hide-sm">Ordered</th>
                    <th scope="col">{canEnter ? 'Result from lab' : 'Status'}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((result) => (
                    <tr key={result.id}>
                      <td>
                        <div className="cell-primary">{result.patient_name}</div>
                        <div className="cell-secondary">
                          {result.patient_mrn} · <Link to={`/lab/orders/${result.lab_order}`}>Order #{result.lab_order}</Link>
                        </div>
                      </td>
                      <td>{result.test_name}</td>
                      <td>{priorityBadge(result.priority)}</td>
                      <td className="hide-sm">{formatDateTime(result.order_date)}</td>
                      <td>
                        {canEnter ? (
                          editingId === result.id ? (
                            <ResultEntryForm result={result} onSaved={saved} onCancel={() => setEditingId(null)} />
                          ) : (
                            <Button variant="secondary" size="sm" onClick={() => { setEditingId(result.id); setFlash('') }}>
                              Enter result
                            </Button>
                          )
                        ) : <Badge tone="info">Pending</Badge>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} count={data.count}
              onPageChange={(next) => update({ page: String(next) })} />
          </>
        ) : (
          <EmptyState icon={FlaskIcon} title={priority ? 'No pending tests match' : 'No pending tests'}>
            Every ordered test has a result.
          </EmptyState>
        )}
      </Panel>
    </>
  )
}
