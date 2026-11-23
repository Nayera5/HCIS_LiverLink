import { getErrorMessage } from '../../api/auth'
import { getMyTreatmentPlans } from '../../api/prescriptions'
import Alert from '../../components/ui/Alert'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { TargetIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { PlanCard } from './PatientTreatmentPlansPanel'
import './Prescriptions.css'

/** Patient portal: own treatment plans (read-only). */
export default function MyTreatmentPlansPage() {
  const { data, error, loading } = useApi(getMyTreatmentPlans)

  return (
    <>
      <PageHeader eyebrow="Patient portal" title="My treatment plans" />
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load your treatment plans.')}</Alert>}
      {loading && !data ? (
        <LoadingBlock label="Loading your treatment plans" />
      ) : data ? (
        data.length ? (
          <div className="rx-plan-list">
            {data.map((plan) => <PlanCard key={plan.id} plan={plan} />)}
          </div>
        ) : (
          <Panel>
            <EmptyState icon={TargetIcon} title="No treatment plans yet">
              Your doctor’s plan for your care appears here.
            </EmptyState>
          </Panel>
        )
      ) : null}
    </>
  )
}
