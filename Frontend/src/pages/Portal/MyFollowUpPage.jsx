import Badge from '../../components/ui/Badge'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { ClockIcon } from '../../components/ui/icons'
import { useApi } from '../../hooks/useApi'
import { listMyFollowUpVisits } from '../../api/transplant'
import { getErrorMessage } from '../../api/auth'

function visitWhen(visit) {
  if (visit.start_time) {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium', timeStyle: 'short',
    }).format(new Date(visit.start_time))
  }
  return visit.due_date
}

/** Patient and donor portal: future post-transplant appointments only. */
export default function MyFollowUpPage() {
  const { data: visits, error, loading } = useApi(listMyFollowUpVisits)
  const upcoming = visits || []

  return (
    <>
      <PageHeader eyebrow="Patient portal" title="My follow-up" />
      {loading ? <LoadingBlock label="Loading follow-up visits" /> : (
        <Panel title="Upcoming follow-up visits" flush={upcoming.length > 0}>
          {error && <p className="error-text">{getErrorMessage(error, 'Could not load your follow-up visits.')}</p>}
          {!error && upcoming.length === 0 && (
            <EmptyState icon={ClockIcon} title="No upcoming follow-up visits">
              Your post-transplant follow-up appointments will appear here when the care team schedules them.
            </EmptyState>
          )}
          {!error && upcoming.length > 0 && (
            <div className="visit-timeline">
              {upcoming.map((visit) => (
                <div className="visit-card" key={visit.id}>
                  <div className="visit-card__info">
                    <span className="visit-card__date">{visitWhen(visit)}</span>
                    <span className="visit-card__detail">
                      {visit.doctor_name ? `With Dr. ${visit.doctor_name}` : 'Your care team'}
                    </span>
                  </div>
                  {visit.get_ready && <Badge tone="warning">Get ready</Badge>}
                </div>
              ))}
            </div>
          )}
        </Panel>
      )}
    </>
  )
}
