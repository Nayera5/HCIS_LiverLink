import { Link } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { countUsers, listUsers } from '../../api/users'
import { useAuth } from '../../auth/authContext'
import { greetingName, roleLine } from '../../auth/roles'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { CheckCircleIcon, UsersIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import StatCard from '../../components/ui/StatCard'
import { useApi } from '../../hooks/useApi'
import { formatDate, greeting, longDate } from '../../utils/format'
import { ReportHighlights } from '../Reports/reportPanels'
import { accountBadge, accountTitle } from '../Users/accountStatus'

async function loadAdminOverview() {
  const [active, staff, patients, needsTitle, inactive, pending, recent] = await Promise.all([
    countUsers({ is_active: 'true' }),
    countUsers({ is_active: 'true', has_staff_profile: 'true' }),
    countUsers({ is_active: 'true', role: 'patient' }),
    countUsers({ is_active: 'true', role: 'clinical_staff', has_staff_profile: 'false' }),
    countUsers({ is_active: 'false' }),
    listUsers({ is_active: 'true', role: 'clinical_staff', has_staff_profile: 'false', page_size: 5 }),
    listUsers({ ordering: '-date_joined', page_size: 6 }),
  ])
  return { counts: { active, staff, patients, needsTitle, inactive }, pending: pending.results, recent: recent.results }
}

export default function AdminDashboard() {
  const { user } = useAuth()
  // loadAdminOverview is a module-level function, so its identity is stable.
  const { data, error, loading } = useApi(loadAdminOverview)
  const counts = data?.counts

  return (
    <>
      <PageHeader
        eyebrow={`${longDate()} · ${roleLine(user)}`}
        title={`${greeting()}, ${greetingName(user)}`}
        actions={
          <Button as={Link} to="/admin/users" variant="secondary">
            Manage users
          </Button>
        }
      />

      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load the account overview.')}</Alert>}

      <div className="stat-grid">
        <StatCard label="Active accounts" value={counts?.active} tone="teal" to="/admin/users?is_active=true"
          hint={counts && `${counts.staff} staff · ${counts.patients} patients & donors`} />
        <StatCard label="Staff accounts" value={counts?.staff} tone="info" to="/admin/users?has_staff_profile=true"
          hint="Active accounts with a job title" />
        <StatCard label="Need a job title" value={counts?.needsTitle} tone="warning"
          to="/admin/users?role=clinical_staff&has_staff_profile=false"
          hint="Clinical accounts without clinical access yet" />
        <StatCard label="Deactivated" value={counts?.inactive} tone="danger" to="/admin/users?is_active=false"
          hint="Cannot sign in · records are kept" />
      </div>

      <div className="content-grid">
        <Panel
          title="Recently created accounts"
          subtitle="Newest first"
          action={<Link to="/admin/users">All users</Link>}
          flush
        >
          {loading && !data ? (
            <LoadingBlock />
          ) : data?.recent.length ? (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Account</th>
                    <th scope="col" className="hide-sm">Role</th>
                    <th scope="col" className="hide-sm">Created</th>
                    <th scope="col">Status</th>
                    <th scope="col"><span className="visually-hidden">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent.map((account) => (
                    <tr key={account.id}>
                      <td>
                        <div className="cell-primary">{account.full_name || account.username}</div>
                        <div className="cell-secondary">@{account.username}</div>
                      </td>
                      <td className="hide-sm">{accountTitle(account)}</td>
                      <td className="hide-sm">{formatDate(account.date_joined)}</td>
                      <td>{accountBadge(account)}</td>
                      <td className="cell-actions">
                        <Link to={`/admin/users/${account.id}`}>View</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState icon={UsersIcon} title="No accounts yet" />
          )}
        </Panel>

        <Panel
          title="Accounts awaiting a job title"
          subtitle="Clinical staff get no clinical access until a job title is assigned"
          divided
          flush
        >
          {loading && !data ? (
            <LoadingBlock />
          ) : data?.pending.length ? (
            <ul className="task-list">
              {data.pending.map((account) => (
                <li key={account.id} className="task-list__item">
                  <div>
                    <p className="cell-primary">{account.full_name || account.username}</p>
                    <p className="cell-secondary">@{account.username} · created {formatDate(account.date_joined)}</p>
                  </div>
                  <Link to={`/admin/users/${account.id}`}>Assign job title</Link>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState icon={CheckCircleIcon} title="All clear">
              Every active clinical account has a job title.
            </EmptyState>
          )}
        </Panel>
      </div>

      <ReportHighlights />
    </>
  )
}
