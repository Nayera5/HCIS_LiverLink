import { useCallback, useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { getHl7Message, listHl7Messages, resendHl7Message } from '../../api/hl7'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock, Pagination } from '../../components/ui/Feedback'
import { MailIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import './HL7.css'

const PAGE_SIZE = 20
const NO_FILTERS = { direction: '', type: '', status: '', search: '' }

const DIRECTION_OPTIONS = [
  { value: 'inbound', label: 'Inbound' },
  { value: 'outbound', label: 'Outbound' },
]
const TYPE_OPTIONS = [
  { value: 'ORM^O01', label: 'ORM^O01 (order)' },
  { value: 'ORU^R01', label: 'ORU^R01 (results)' },
]
const STATUSES = {
  queued: { label: 'Queued', tone: 'warning' },
  received: { label: 'Received', tone: 'info' },
  processed: { label: 'Processed', tone: 'success' },
  sent: { label: 'Sent', tone: 'success' },
  error: { label: 'Error', tone: 'danger' },
}
const STATUS_OPTIONS = Object.entries(STATUSES).map(([value, { label }]) => ({ value, label }))

const statusBadge = (status) => <Badge tone={STATUSES[status]?.tone}>{STATUSES[status]?.label || status}</Badge>
const ackBadge = (code) => (code ? <Badge tone={code === 'AA' ? 'success' : 'danger'}>{code}</Badge> : '—')
const directionBadge = (direction) =>
  direction === 'inbound' ? <Badge tone="purple">← Inbound</Badge> : <Badge tone="teal">→ Outbound</Badge>

/** Log of every HL7 message sent or received (route guarded by `hl7.monitor`). */
export default function HL7MonitorPage() {
  const [filters, setFilters] = useState(NO_FILTERS)
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState(null)

  const loader = useCallback(
    () => listHl7Messages({ ...filters, page: page > 1 ? page : '', page_size: PAGE_SIZE }),
    [filters, page],
  )
  const { data, error, loading, reload } = useApi(loader)

  const setFilter = (key) => (event) => {
    setFilters((prev) => ({ ...prev, [key]: event.target.value }))
    setPage(1)
  }

  const select = (id) => {
    setSelectedId(id)
    window.scrollTo({ top: 0, behavior: 'smooth' }) // the message opens above the table
  }

  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="HL7 message monitor"
        actions={<Button variant="secondary" onClick={reload} loading={loading}>Refresh</Button>}
      />

      {selectedId && (
        <MessageDetail key={selectedId} id={selectedId} onClose={() => setSelectedId(null)} onChanged={reload} />
      )}

      <Panel flush>
        <div className="hl7-filters">
          <SelectField label="Direction" placeholder="All" options={DIRECTION_OPTIONS}
            value={filters.direction} onChange={setFilter('direction')} />
          <SelectField label="Type" placeholder="All" options={TYPE_OPTIONS}
            value={filters.type} onChange={setFilter('type')} />
          <SelectField label="Status" placeholder="All" options={STATUS_OPTIONS}
            value={filters.status} onChange={setFilter('status')} />
          <TextField label="Search" name="search" placeholder="MRN or control ID"
            value={filters.search} onChange={setFilter('search')} />
        </div>

        {error && (
          <div className="panel-inset">
            <Alert variant="error">{getErrorMessage(error, 'Could not load the HL7 messages.')}</Alert>
          </div>
        )}

        {loading && !data ? (
          <LoadingBlock label="Loading HL7 messages" />
        ) : data?.results.length ? (
          <>
            <div className="table-wrap" aria-busy={loading}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">When</th>
                    <th scope="col">Direction</th>
                    <th scope="col">Message</th>
                    <th scope="col">System</th>
                    <th scope="col">Patient</th>
                    <th scope="col">ACK</th>
                    <th scope="col">Status</th>
                    <th scope="col"><span className="visually-hidden">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((msg) => (
                    <tr key={msg.id} className={msg.id === selectedId ? 'hl7-row--selected' : undefined}>
                      <td className="hl7-nowrap">{formatDateTime(msg.created_at)}</td>
                      <td>{directionBadge(msg.direction)}</td>
                      <td>
                        <div className="cell-primary">{msg.message_type}</div>
                        <div className="cell-secondary hl7-mono">{msg.control_id || '—'}</div>
                      </td>
                      <td>{msg.system_name || 'Unknown'}</td>
                      <td className="hl7-nowrap">{msg.patient_mrn || '—'}</td>
                      <td>{ackBadge(msg.ack_code)}</td>
                      <td>
                        {statusBadge(msg.status)}
                        {msg.error_text && <div className="cell-secondary hl7-error">{msg.error_text}</div>}
                      </td>
                      <td className="cell-actions">
                        <Button variant="link" onClick={() => select(msg.id)}
                          aria-label={`View message ${msg.control_id}`}>View</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} count={data.count} onPageChange={setPage} />
          </>
        ) : !error && (
          <EmptyState icon={MailIcon} title="No HL7 messages">
            Orders sent to the external lab and results received from it appear here.
          </EmptyState>
        )}
      </Panel>
    </>
  )
}

/** Raw message next to its acknowledgement, with "Resend" for a failed outbound message. */
function MessageDetail({ id, onClose, onChanged }) {
  const loader = useCallback(() => getHl7Message(id), [id])
  const { data: msg, error, setData } = useApi(loader)
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState('')

  async function resend() {
    setBusy(true)
    setProblem('')
    try {
      setData(await resendHl7Message(id))
      onChanged()
    } catch (err) {
      setProblem(getErrorMessage(err, 'Could not resend the message.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Panel
      className="hl7-detail"
      title={msg ? `${msg.message_type} · ${msg.control_id || 'no control ID'}` : 'HL7 message'}
      subtitle={msg ? `${msg.direction === 'inbound' ? 'From' : 'To'} ${msg.system_name || 'unknown system'}, ${formatDateTime(msg.created_at)}` : undefined}
      action={
        <div className="hl7-detail__actions">
          {msg?.can_resend && <Button size="sm" onClick={resend} loading={busy}>Resend</Button>}
          <Button size="sm" variant="secondary" onClick={onClose}>Close</Button>
        </div>
      }
    >
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load this message.')}</Alert>}
      {problem && <Alert variant="error">{problem}</Alert>}
      {!msg && !error && <LoadingBlock label="Loading message" />}
      {msg && (
        <>
          {msg.error_text && <Alert variant="error">{msg.error_text}</Alert>}
          <div className="hl7-detail__columns">
            <RawMessage title="Message" text={msg.raw_message} />
            <RawMessage title="Acknowledgement" text={msg.ack_message} empty="No acknowledgement yet." />
          </div>
        </>
      )}
    </Panel>
  )
}

/** One HL7 segment per line, segment name highlighted. */
function RawMessage({ title, text, empty }) {
  const lines = (text || '').split(/\r\n|\r|\n/).filter(Boolean)
  return (
    <div>
      <h3 className="hl7-raw__title">{title}</h3>
      {lines.length ? (
        <pre className="hl7-raw" tabIndex={0}>
          {lines.map((line, index) => (
            <div key={index}><strong>{line.slice(0, 3)}</strong>{line.slice(3)}</div>
          ))}
        </pre>
      ) : <p className="muted-text">{empty}</p>}
    </div>
  )
}
