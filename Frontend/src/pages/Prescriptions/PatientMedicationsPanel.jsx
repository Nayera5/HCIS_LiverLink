import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { completePrescription, getPatientMedications, stopPrescription } from '../../api/prescriptions'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { PillIcon } from '../../components/ui/icons'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { periodText, rxStatusBadge } from './rxBadges'
import { ReasonDialog } from './rxDisplay'
import { regimenText } from './rxFormat'
import './Prescriptions.css'

/** Current / past tab switcher shared by the staff panel and the portal page. */
export function MedicationTabs({ tab, onChange, counts }) {
  return (
    <div className="rx-tabs" role="tablist" aria-label="Medications">
      {[['current', 'Current'], ['past', 'Past']].map(([key, label]) => (
        <button key={key} type="button" role="tab" aria-selected={tab === key}
          className={`rx-tabs__tab ${tab === key ? 'rx-tabs__tab--on' : ''}`} onClick={() => onChange(key)}>
          {label} <span className="rx-tabs__count">{counts[key]}</span>
        </button>
      ))}
    </div>
  )
}

export function MedicationTable({ items, showPrescriber = true, actions }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Medication</th>
            <th scope="col">Regimen</th>
            <th scope="col" className="hide-sm">Period</th>
            <th scope="col">Status</th>
            {showPrescriber && <th scope="col" className="hide-sm">Prescribed by</th>}
            {actions && <th scope="col"><span className="visually-hidden">Actions</span></th>}
          </tr>
        </thead>
        <tbody>
          {items.map((rx) => (
            <tr key={rx.id}>
              <td>
                <div className="cell-primary">{rx.drug_name}</div>
                {rx.instructions && <div className="cell-secondary">{rx.instructions}</div>}
                {rx.encounter && (
                  <div className="cell-secondary">
                    <Link to={`/encounters/${rx.encounter}`}>Visit #{rx.encounter}</Link>
                  </div>
                )}
                {rx.status === 'stopped' && rx.stop_reason && (
                  <div className="cell-secondary">Stopped {formatDateTime(rx.stopped_at)}: {rx.stop_reason}</div>
                )}
              </td>
              <td>{regimenText(rx)}</td>
              <td className="hide-sm">{periodText(rx)}</td>
              <td>{rxStatusBadge(rx)}</td>
              {showPrescriber && <td className="hide-sm">{rx.prescribed_by_name}</td>}
              {actions && <td className="rx-actions-cell">{actions(rx)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Medications section of the medical record (staff with prescriptions.view). */
export default function PatientMedicationsPanel({ patientId }) {
  const { can } = useAuth()
  const canPrescribe = can('prescriptions.prescribe')
  const loader = useCallback(() => getPatientMedications(patientId), [patientId])
  const { data, error, loading, reload } = useApi(loader)
  const [tab, setTab] = useState('current')
  const [pending, setPending] = useState(null) // { rx, kind: 'stop' | 'complete' }
  const [flash, setFlash] = useState('')

  const act = async (reason) => {
    const { rx, kind } = pending
    if (kind === 'stop') await stopPrescription(rx.id, reason)
    else await completePrescription(rx.id, reason)
    setPending(null)
    setFlash(`${rx.drug_name} ${kind === 'stop' ? 'stopped' : 'marked as completed'}.`)
    reload()
  }

  const rowActions = canPrescribe
    ? (rx) => rx.status === 'active' && (
      <div className="inline-actions">
        <Button variant="secondary" size="sm" onClick={() => setPending({ rx, kind: 'complete' })}>Complete</Button>
        <Button variant="secondary" size="sm" onClick={() => setPending({ rx, kind: 'stop' })}>Stop</Button>
      </div>
    )
    : null

  const items = data ? data[tab] : []

  return (
    <Panel title="Medications" subtitle="Current and past prescriptions" collapsible>
      {flash && <Alert variant="success">{flash}</Alert>}
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load medications.')}</Alert>}
      {loading && !data ? (
        <LoadingBlock label="Loading medications" />
      ) : data ? (
        <div className="content-stack">
          <MedicationTabs tab={tab} onChange={setTab} counts={{ current: data.current.length, past: data.past.length }} />
          {items.length ? (
            <MedicationTable items={items} actions={rowActions} />
          ) : (
            <EmptyState icon={PillIcon} title={tab === 'current' ? 'No current medications' : 'No past medications'}>
              {tab === 'current' && canPrescribe ? 'Prescriptions created during encounters appear here.' : null}
            </EmptyState>
          )}
        </div>
      ) : null}
      <ReasonDialog
        key={pending ? `${pending.kind}-${pending.rx.id}` : 'none'}
        open={Boolean(pending)}
        title={pending?.kind === 'stop' ? `Stop ${pending.rx.drug_name}?` : `Complete ${pending?.rx.drug_name}?`}
        confirmLabel={pending?.kind === 'stop' ? 'Stop medication' : 'Mark completed'}
        tone={pending?.kind === 'stop' ? 'danger' : 'primary'}
        required={pending?.kind === 'stop'}
        onConfirm={act}
        onCancel={() => setPending(null)}>
        {pending && <p>{regimenText(pending.rx)} · {periodText(pending.rx)}</p>}
      </ReasonDialog>
    </Panel>
  )
}
