import { Link } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import Alert from '../../components/ui/Alert'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { ClipboardIcon } from '../../components/ui/icons'
import Panel from '../../components/ui/Panel'
import StatCard from '../../components/ui/StatCard'
import { formatDate } from '../../utils/format'
import { ageSex, categoryBadge, patientName } from '../Patients/patientDisplay'

/** Registry KPIs + recently registered patients (for staff with patients.view). Real data only. */
export function PatientStats({ data }) {
  const counts = data?.summary.by_category
  return (
    <div className="stat-grid">
      <StatCard label="Registered patients" value={data?.summary.total} tone="teal" to="/patients"
        hint="All categories" />
      <StatCard label="Liver patients" value={counts?.liver_patient} tone="neutral" to="/patients?category=liver_patient"
        hint="Under hepatology care" />
      <StatCard label="Transplant recipients" value={counts?.recipient} tone="info" to="/patients?category=recipient"
        hint="Transplant candidates" />
      <StatCard label="Living donors" value={counts?.donor} tone="warning" to="/patients?category=donor"
        hint="Registered as donors" />
    </div>
  )
}

export function RecentPatientsPanel({ data, loading }) {
  return (
    <Panel title="Recently registered patients" subtitle="Newest first" action={<Link to="/patients">All patients</Link>} flush>
      {loading && !data ? (
        <LoadingBlock />
      ) : data?.recent.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Patient</th>
                <th scope="col">Category</th>
                <th scope="col" className="hide-sm">Registered</th>
                <th scope="col"><span className="visually-hidden">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {data.recent.map((patient) => (
                <tr key={patient.id}>
                  <td>
                    <div className="cell-primary">{patientName(patient)}</div>
                    <div className="cell-secondary">{patient.mrn} · {ageSex(patient)}</div>
                  </td>
                  <td>{categoryBadge(patient.category)}</td>
                  <td className="hide-sm">{formatDate(patient.created_at)}</td>
                  <td className="cell-actions"><Link to={`/patients/${patient.id}`}>Open</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState icon={ClipboardIcon} title="No patients registered yet" />
      )}
    </Panel>
  )
}

export function PatientOverviewError({ error }) {
  return error ? <Alert variant="error" className="dashboard-notice">{getErrorMessage(error, 'Could not load patient data.')}</Alert> : null
}
