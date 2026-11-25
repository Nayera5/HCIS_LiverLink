import { Link } from 'react-router-dom'
import { loadPatientOverview } from '../../api/patients'
import { useAuth } from '../../auth/authContext'
import { greetingName, roleLine } from '../../auth/roles'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { greeting, longDate } from '../../utils/format'
import { ReportHighlights } from '../Reports/reportPanels'
import { PatientOverviewError, PatientStats, RecentPatientsPanel } from './PatientOverview'

function ProfilePanel({ user }) {
  const profile = user.staff_profile
  return (
    <Panel title="Your profile" action={<Link to="/profile">Edit contact details</Link>}>
      <dl className="detail-list">
        <div><dt>Username</dt><dd>{user.username}</dd></div>
        <div><dt>Job title</dt><dd>{profile?.job_title_display || 'Not assigned'}</dd></div>
        <div><dt>Department</dt><dd>{profile?.department || '—'}</dd></div>
        <div><dt>License number</dt><dd>{profile?.license_no || '—'}</dd></div>
        <div><dt>Email</dt><dd>{user.email || '—'}</dd></div>
        <div><dt>Phone</dt><dd>{profile?.phone || '—'}</dd></div>
      </dl>
    </Panel>
  )
}

/** Clinical staff with patient access: registry overview built from real data. */
function ClinicalWorkspace() {
  const { data, error, loading } = useApi(loadPatientOverview)
  return (
    <>
      <PatientOverviewError error={error} />
      <PatientStats data={data} />
      <RecentPatientsPanel data={data} loading={loading} />
    </>
  )
}

/**
 * Dashboard for clinical staff and non-super admins. Content follows the user's own job title
 * and capabilities; modules not yet delivered are not shown.
 */
export default function StaffDashboard() {
  const { user, can } = useAuth()
  const profile = user.staff_profile
  const eyebrow = [longDate(), roleLine(user), profile?.department].filter(Boolean).join(' · ')

  return (
    <>
      <PageHeader
        eyebrow={eyebrow}
        title={`${greeting()}, ${greetingName(user)}`}
        actions={
          <>
            {can('patients.view') && (
              <Button as={Link} to="/patients" variant="secondary">Patients</Button>
            )}
            <Button as={Link} to="/profile" variant="secondary">My profile</Button>
          </>
        }
      />

      {!user.job_title && (
        <Alert variant="warning" className="dashboard-notice">
          <strong>Your account does not have a job title yet.</strong> An administrator must assign
          one before you can open patient records or other clinical features.
        </Alert>
      )}

      {can('patients.view') ? (
        <ClinicalWorkspace />
      ) : (
        <ProfilePanel user={user} />
      )}

      {/* Charts for the reports this job title may open (nothing for other roles). */}
      <ReportHighlights />
    </>
  )
}
