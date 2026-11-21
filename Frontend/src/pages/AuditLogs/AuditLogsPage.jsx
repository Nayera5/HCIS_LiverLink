import { useCallback, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { listAuditLogs } from '../../api/auditLogs'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock, Pagination } from '../../components/ui/Feedback'
import { ShieldIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import {
  ACTION_OPTIONS, KIND_OPTIONS, actionChange, actionLabel, describeRecord, entryKind, hasActiveFilters,
  kindParam, readFilters, toApiParams, validateFilters,
} from './auditLogFilters'
import './AuditLogs.css'

const PAGE_SIZE = 50
const TYPED_KEYS = ['user', 'patient', 'date_from', 'date_to'] // applied with the "Apply" button

/**
 * Super Admin audit log viewer (route guarded by `audit.view`; the backend enforces the same).
 * Read-only. Filters live in the URL, so a filtered view can be bookmarked or shared.
 * Opens on write operations; profile access (reads) is shown with Type = All or Reads.
 */
export default function AuditLogsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = readFilters(searchParams)
  const page = Number(searchParams.get('page')) || 1

  const query = searchParams.toString()
  const loader = useCallback(() => {
    const params = new URLSearchParams(query)
    const pageParam = Number(params.get('page')) || 1
    return listAuditLogs({ ...toApiParams(readFilters(params)), page: pageParam > 1 ? pageParam : '', page_size: PAGE_SIZE })
  }, [query])
  const { data, error, loading } = useApi(loader)

  const update = (changes) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)))
    if (!('page' in changes)) next.delete('page')
    setSearchParams(next)
  }

  const hasFilters = hasActiveFilters(filters)
  const typedKey = TYPED_KEYS.map((key) => filters[key]).join('|')

  return (
    <>
      <PageHeader eyebrow="Administration" title="Audit logs" />

      <Panel flush>
        <div className="audit-filters">
          <SelectField
            label="Action"
            placeholder="All actions"
            options={ACTION_OPTIONS}
            value={filters.action}
            onChange={(event) => {
              const changes = actionChange(event.target.value, filters.kind)
              update('kind' in changes ? { ...changes, kind: kindParam(changes.kind) } : changes)
            }}
          />
          <SelectField
            label="Type"
            options={KIND_OPTIONS}
            value={filters.kind}
            hint={filters.kind === 'write' ? 'Choose All or Reads to see profile access.' : undefined}
            onChange={(event) => update({ kind: kindParam(event.target.value) })}
          />
          {/* Remounted when the URL changes (e.g. a row's "filter" link), so the inputs stay in sync. */}
          <TypedFilters key={typedKey} filters={filters} onApply={update} />
          {hasFilters && (
            <Button variant="link" className="audit-filters__clear" onClick={() => setSearchParams(new URLSearchParams())}>
              Clear filters
            </Button>
          )}
        </div>

        {error && (
          <div className="panel-inset">
            <Alert variant="error">{getErrorMessage(error, 'Could not load the audit log.')}</Alert>
          </div>
        )}

        {loading && !data ? (
          <LoadingBlock label="Loading audit log" />
        ) : data?.results.length ? (
          <>
            <div className="table-wrap" aria-busy={loading}>
              <table className="data-table audit-table">
                <thead>
                  <tr>
                    <th scope="col">When</th>
                    <th scope="col">Who</th>
                    <th scope="col">Action</th>
                    <th scope="col">Record</th>
                    <th scope="col">Patient</th>
                    <th scope="col" className="hide-sm">IP address</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((entry) => {
                    const kind = entryKind(entry)
                    return (
                      <tr key={entry.id}>
                        <td className="audit-table__when">{formatDateTime(entry.timestamp)}</td>
                        <td>
                          <div className="cell-primary">{entry.actor || '—'}</div>
                          {entry.user_id != null && (
                            <button type="button" className="audit-filter-link"
                              onClick={() => update({ user: String(entry.user_id) })}
                              aria-label={`Show only entries by user #${entry.user_id}`}>
                              User #{entry.user_id}
                            </button>
                          )}
                        </td>
                        <td>
                          <div className="audit-action">
                            <Badge tone={kind.tone}>{kind.label}</Badge>
                            <span>{entry.action_label || actionLabel(entry.action)}</span>
                          </div>
                        </td>
                        <td>{describeRecord(entry)}</td>
                        <td>
                          {entry.patient ? (
                            <>
                              <div className="cell-primary">{entry.patient.name}</div>
                              <button type="button" className="audit-filter-link"
                                onClick={() => update({ patient: String(entry.patient.id) })}
                                aria-label={`Show only entries for patient ${entry.patient.mrn}`}>
                                {entry.patient.mrn}
                              </button>
                            </>
                          ) : '—'}
                        </td>
                        <td className="hide-sm audit-table__ip">{entry.ip_address || '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} count={data.count}
              onPageChange={(next) => update({ page: String(next) })} />
          </>
        ) : (
          <EmptyState icon={ShieldIcon} title={hasFilters ? 'No entries match these filters' : 'No write operations recorded yet'}>
            {hasFilters ? 'Try different filters or clear them.' : 'Staff, patient and donor changes will appear here.'}
          </EmptyState>
        )}
      </Panel>
    </>
  )
}

/** User ID, patient ID and date range: edited locally, validated, then applied together. */
function TypedFilters({ filters, onApply }) {
  const [draft, setDraft] = useState(() => Object.fromEntries(TYPED_KEYS.map((key) => [key, filters[key]])))
  const [errors, setErrors] = useState({})
  const set = (key) => (event) => setDraft((prev) => ({ ...prev, [key]: event.target.value }))

  const apply = (event) => {
    event.preventDefault()
    const found = validateFilters(draft)
    setErrors(found)
    if (Object.keys(found).length === 0) {
      onApply(Object.fromEntries(TYPED_KEYS.map((key) => [key, draft[key].trim()])))
    }
  }

  return (
    <form className="audit-filters__typed" onSubmit={apply} noValidate>
      <TextField label="User ID" name="user" inputMode="numeric" placeholder="Any user"
        value={draft.user} onChange={set('user')} error={errors.user} />
      <TextField label="Patient ID" name="patient" inputMode="numeric" placeholder="Any patient"
        value={draft.patient} onChange={set('patient')} error={errors.patient} />
      <TextField label="From" name="date_from" type="date"
        value={draft.date_from} onChange={set('date_from')} error={errors.date_from} />
      <TextField label="To" name="date_to" type="date"
        value={draft.date_to} onChange={set('date_to')} error={errors.date_to} />
      <Button type="submit" variant="outline" className="audit-filters__apply">Apply</Button>
    </form>
  )
}
