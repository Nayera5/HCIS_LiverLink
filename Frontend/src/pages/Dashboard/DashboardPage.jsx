import { useAuth } from '../../auth/authContext'
import AdminDashboard from './AdminDashboard'
import PatientDashboard from './PatientDashboard'
import StaffDashboard from './StaffDashboard'

/** Picks the dashboard for the signed-in user's role; each shows only role-relevant content. */
export default function DashboardPage() {
  const { user, can } = useAuth()
  if (user.role === 'patient') return <PatientDashboard />
  if (can('users.manage')) return <AdminDashboard />
  return <StaffDashboard />
}
