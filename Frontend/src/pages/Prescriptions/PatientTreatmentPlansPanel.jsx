import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import {
  cancelTreatmentPlan, completeTreatmentPlan, listTreatmentPlans, updateTreatmentPlan,
} from '../../api/prescriptions'
import { loadAllPages } from '../../api/pagination'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { TargetIcon } from '../../components/ui/icons'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDate, formatDateTime } from '../../utils/format'
import PlanForm from './PlanForm'
import { planStatusBadge } from './rxBadges'
import { ReasonDialog, ReviewDate } from './rxDisplay'
import { PLAN_TYPE_LABELS } from './rxFormat'
import './Prescriptions.css'

/** One plan as a card: type, status, goals, steps and dates. `actions` renders on active plans. */
export function PlanCard({ plan, actions }) {
  return (
    <article className="rx-plan">
      <header className="rx-plan__header">
        <div>
          <h3 className="rx-plan__title">{PLAN_TYPE_LABELS[plan.plan_type] || plan.plan_type}</h3>
          <p className="cell-secondary">
            Started {formatDate(plan.start_date)} · by {plan.created_by_name}
            {plan.updated_at && ` · updated ${formatDateTime(plan.updated_at)}`}
          </p>
        </div>
        {planStatusBadge(plan.status)}
      </header>
      <dl className="rx-plan__body">
        {plan.encounter && (
          <div><dt>Encounter</dt><dd><Link to={`/encounters/${plan.encounter}`}>Visit #{plan.encounter}</Link></dd></div>
        )}
        <div><dt>Goals</dt><dd className="rx-pre">{plan.goals}</dd></div>
        {plan.steps && <div><dt>Steps</dt><dd className="rx-pre">{plan.steps}</dd></div>}
        <div><dt>Review date</dt><dd>{plan.review_date ? <ReviewDate plan={plan} /> : '—'}</dd></div>
      </dl>
      {actions && plan.status === 'active' && <footer className="inline-actions">{actions}</footer>}
    </article>
  )
}

/** Treatment plans section of the medical record (staff with treatment_plans.view). */
export default function PatientTreatmentPlansPanel({ patientId }) {
  const { can } = useAuth()
  const canManage = can('treatment_plans.manage')
  const loader = useCallback(() => loadAllPages(listTreatmentPlans, { patient: patientId }), [patientId])
  const { data, error, loading, reload } = useApi(loader)
  const [mode, setMode] = useState(null) // plan id being edited
  const [closing, setClosing] = useState(null) // { plan, kind: 'complete' | 'cancel' }
  const [flash, setFlash] = useState('')

  const done = (message) => {
    setMode(null)
    setClosing(null)
    setFlash(message)
    reload()
  }

  const update = (plan) => async (payload) => {
    const updated = await updateTreatmentPlan(plan.id, payload)
    done(updated.transplant_case_id
      ? `Treatment plan updated. Transplant case #${updated.transplant_case_id} ${updated.transplant_case_created ? 'was created' : 'is already open'}. Donor matching is available only while the case is under evaluation.`
      : 'Treatment plan updated. The change and reason were recorded in the audit log.')
  }

  const close = async (reason) => {
    const { plan, kind } = closing
    await (kind === 'complete' ? completeTreatmentPlan : cancelTreatmentPlan)(plan.id, reason)
    done(`Treatment plan ${kind === 'complete' ? 'completed' : 'cancelled'}.`)
  }

  const plans = data || []
  return (
    <Panel title="Treatment plans" subtitle="Goals, steps and review dates" collapsible>
      {flash && <Alert variant="success">{flash}</Alert>}
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load treatment plans.')}</Alert>}
      {loading && !data ? (
        <LoadingBlock label="Loading treatment plans" />
      ) : data ? (
        plans.length ? (
          <div className="rx-plan-list">
            {plans.map((plan) => (mode === plan.id ? (
              <div key={plan.id} className="rx-plan rx-plan--editing">
                <h3 className="rx-plan__title">Edit {PLAN_TYPE_LABELS[plan.plan_type]} plan</h3>
                <PlanForm plan={plan} onSubmit={update(plan)} onCancel={() => setMode(null)}
                  canReferTransplant={can('transplant.refer')} />
              </div>
            ) : (
              <PlanCard key={plan.id} plan={plan} actions={canManage && (
                <>
                  <Button variant="secondary" size="sm" onClick={() => { setMode(plan.id); setFlash('') }}>Edit</Button>
                  <Button variant="secondary" size="sm" onClick={() => setClosing({ plan, kind: 'complete' })}>Complete</Button>
                  <Button variant="secondary" size="sm" onClick={() => setClosing({ plan, kind: 'cancel' })}>Cancel plan</Button>
                </>
              )} />
            )))}
          </div>
        ) : (
          <EmptyState icon={TargetIcon} title="No treatment plans yet">
            {canManage ? 'Treatment plans created during encounters appear here.' : null}
          </EmptyState>
        )
      ) : null}
      <ReasonDialog
        key={closing ? `${closing.kind}-${closing.plan.id}` : 'none'}
        open={Boolean(closing)}
        title={closing?.kind === 'complete' ? 'Complete this plan?' : 'Cancel this plan?'}
        confirmLabel={closing?.kind === 'complete' ? 'Complete plan' : 'Cancel plan'}
        tone={closing?.kind === 'cancel' ? 'danger' : 'primary'}
        onConfirm={close}
        onCancel={() => setClosing(null)}>
        <p>A closed plan can no longer be edited.</p>
      </ReasonDialog>
    </Panel>
  )
}
