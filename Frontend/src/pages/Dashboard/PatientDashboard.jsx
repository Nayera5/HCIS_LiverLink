import { Link } from 'react-router-dom'
import { getMyRecordSummary } from '../../api/patients'
import { useAuth } from '../../auth/authContext'
import { greetingName } from '../../auth/roles'
import Button from '../../components/ui/Button'
import { LoadingBlock } from '../../components/ui/Feedback'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { greeting, longDate } from '../../utils/format'
import { categoryBadge } from '../Patients/patientDisplay'

/** Patient & donor portal home: own record summary and self-service only. */
export default function PatientDashboard() {
  const { user } = useAuth()
  const { data: record, error, loading } = useApi(getMyRecordSummary)

  return (
    <>
      <PageHeader
        eyebrow={`${longDate()} · Patient portal`}
        title={`${greeting()}, ${greetingName(user)}`}
        actions={<Button as={Link} to="/my-medical-record" variant="secondary">Medical record</Button>}
      />

      <Panel title="Your hospital record" action={record && <Link to="/my-medical-record">Open record</Link>}>
        {loading && !record ? (
          <LoadingBlock />
        ) : record ? (
          <dl className="detail-list">
            <div><dt>Medical Record Number</dt><dd>{record.mrn}</dd></div>
            <div><dt>Category</dt><dd>{categoryBadge(record.category)}</dd></div>
            <div><dt>Phone</dt><dd>{record.phone}</dd></div>
            <div><dt>Email</dt><dd>{user.email || 'Not set'}</dd></div>
          </dl>
        ) : (
          <p className="muted-text">
            {error?.status === 404 ? error.data?.detail : 'Your record could not be loaded right now.'}
          </p>
        )}
      </Panel>
    </>
  )
}
