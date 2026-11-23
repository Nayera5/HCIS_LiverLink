import { getErrorMessage } from '../../api/auth'
import { getMyConsents } from '../../api/consents'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { CheckCircleIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { STATUS_LABELS, STATUS_TONES } from '../Consents/consentRules'
import '../Patients/Patients.css'
import '../Consents/Consents.css'

/** Portal: own consents, read-only (self.consents). Changes are made with the hospital team. */
export default function MyConsentsPage() {
  const { data: consents, error, loading } = useApi(getMyConsents)
  const header = <PageHeader eyebrow="Patient portal" title="My consents" />

  if (loading && !consents) return <>{header}<LoadingBlock label="Loading your consents" /></>
  if (error && !consents) {
    return (
      <>
        {header}
        <Panel>
          {error.status === 404
            ? <EmptyState icon={CheckCircleIcon} title="No hospital record yet">{error.data?.detail}</EmptyState>
            : <Alert variant="error">{getErrorMessage(error, 'Could not load your consents.')}</Alert>}
        </Panel>
      </>
    )
  }

  return (
    <>
      {header}
      <Panel title="Signed consents" subtitle="To sign or withdraw a consent, please speak to your transplant team.">
        {consents.length ? (
          <ul className="consent-list">
            {consents.map((consent) => (
              <li key={consent.id} className={`consent-item ${consent.status === 'withdrawn' ? 'consent-item--withdrawn' : ''}`}>
                <div className="consent-item__head">
                  <span className="cell-primary">{consent.type_label}</span>
                  <Badge tone={STATUS_TONES[consent.status]}>{STATUS_LABELS[consent.status]}</Badge>
                </div>
                <dl className="detail-list">
                  <div><dt>Signed on</dt><dd>{formatDateTime(consent.signed_at)}</dd></div>
                  <div><dt>Witness</dt><dd>{consent.witnessed_by || '—'}</dd></div>
                  {consent.withdrawn_at && <div><dt>Withdrawn on</dt><dd>{formatDateTime(consent.withdrawn_at)}</dd></div>}
                </dl>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState icon={CheckCircleIcon} title="No consents recorded">
            Consents you sign with the transplant team will appear here.
          </EmptyState>
        )}
      </Panel>
    </>
  )
}
