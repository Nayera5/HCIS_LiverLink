import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { listTreatmentPlans } from '../../api/prescriptions'
import Alert from '../../components/ui/Alert'
import { EmptyState, LoadingBlock, Pagination } from '../../components/ui/Feedback'
import { TargetIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { ReviewDate } from './rxDisplay'
import { PLAN_TYPE_LABELS } from './rxFormat'
import './Prescriptions.css'

const PAGE_SIZE = 20

/** /rx/reviews  Active treatment plans whose review date is today or has passed. */
export default function PlanReviewsPage() {
  const [page, setPage] = useState(1)
  const loader = useCallback(() => listTreatmentPlans({ review_due: 1, page, page_size: PAGE_SIZE }), [page])
  const { data, error, loading } = useApi(loader)

  return (
    <>
      <PageHeader eyebrow="Treatment plans" title="Plan reviews due" />
      <Panel flush title="Due for review" subtitle="Active plans whose review date is today or already passed.">
        {error && <Alert variant="error">{getErrorMessage(error, 'Could not load plans.')}</Alert>}
        {loading && !data ? (
          <LoadingBlock label="Loading plans" />
        ) : data?.results.length ? (
          <>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Patient</th>
                    <th scope="col">Plan</th>
                    <th scope="col">Review date</th>
                    <th scope="col" className="hide-sm">Doctor</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((plan) => (
                    <tr key={plan.id}>
                      <td>
                        <Link className="cell-primary" to={`/patients/${plan.patient}`}>{plan.patient_name}</Link>
                        <div className="cell-secondary">{plan.patient_mrn}</div>
                      </td>
                      <td>{PLAN_TYPE_LABELS[plan.plan_type] || plan.plan_type}</td>
                      <td><ReviewDate plan={plan} /></td>
                      <td className="hide-sm">{plan.created_by_name}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} count={data.count} onPageChange={setPage} />
          </>
        ) : data ? (
          <EmptyState icon={TargetIcon} title="No reviews due">All active plans are within their review date.</EmptyState>
        ) : null}
      </Panel>
    </>
  )
}
