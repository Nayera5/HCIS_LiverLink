import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AuthProvider from './auth/AuthProvider'
import { PublicOnly, RequireAuth, RequireCapability } from './auth/guards'
import AppShell from './components/layout/AppShell'
import AuditLogsPage from './pages/AuditLogs/AuditLogsPage'
import ForgotPasswordPage from './pages/Auth/ForgotPasswordPage'
import RegisterPage from './pages/Auth/RegisterPage'
import ResetPasswordPage from './pages/Auth/ResetPasswordPage'
import DashboardPage from './pages/Dashboard/DashboardPage'
import NotFoundPage from './pages/Errors/NotFoundPage'
import LoginRoute from './pages/Login/LoginRoute'
import PatientDetailPage from './pages/Patients/PatientDetailPage'
import PatientRegisterPage from './pages/Patients/PatientRegisterPage'
import PatientsPage from './pages/Patients/PatientsPage'
import LabOrderCreatePage from './pages/Labs/LabOrderCreatePage'
import LabOrderDetailPage from './pages/Labs/LabOrderDetailPage'
import LabOrdersPage from './pages/Labs/LabOrdersPage'
import MyLabOrdersPage from './pages/Labs/MyLabOrdersPage'
import MyLabResultsPage from './pages/Labs/MyLabResultsPage'
import PendingTestsPage from './pages/Labs/PendingTestsPage'
import MyRecordPage from './pages/Portal/MyRecordPage'
import MyMedicationsPage from './pages/Prescriptions/MyMedicationsPage'
import MyTreatmentPlansPage from './pages/Prescriptions/MyTreatmentPlansPage'
import PlanReviewsPage from './pages/Prescriptions/PlanReviewsPage'
import PrescribePage from './pages/Prescriptions/PrescribePage'
import ProfilePage from './pages/Profile/ProfilePage'
import UserCreatePage from './pages/Users/UserCreatePage'
import UserDetailPage from './pages/Users/UserDetailPage'
import UsersPage from './pages/Users/UsersPage'

/*
 * Routes. Pages inside <RequireAuth> use the app shell (sidebar + top bar).
 * Each module adds its pages here; wrap them in <RequireCapability> to match the backend rules.
 */
function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginRoute />} />
          <Route element={<PublicOnly />}>
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
          </Route>

          <Route element={<RequireAuth />}>
            <Route element={<AppShell />}>
              <Route index element={<DashboardPage />} />
              <Route path="profile" element={<ProfilePage />} />

              <Route element={<RequireCapability capability="patients.view" />}>
                <Route path="patients" element={<PatientsPage />} />
                <Route path="patients/:id" element={<PatientDetailPage />} />
              </Route>
              <Route element={<RequireCapability capability="patients.register" />}>
                <Route path="patients/new" element={<PatientRegisterPage />} />
              </Route>
              <Route element={<RequireCapability capability="self.patient_record" />}>
                <Route path="my-record" element={<MyRecordPage />} />
              </Route>

              <Route element={<RequireCapability capability="labs.view" />}>
                <Route path="lab/orders" element={<LabOrdersPage />} />
                <Route path="lab/orders/:id" element={<LabOrderDetailPage />} />
                <Route path="lab/pending" element={<PendingTestsPage />} />
              </Route>
              <Route element={<RequireCapability capability="labs.order" />}>
                <Route path="lab/orders/new" element={<LabOrderCreatePage />} />
              </Route>
              <Route element={<RequireCapability capability="self.lab_results" />}>
                <Route path="my-results" element={<MyLabResultsPage />} />
                <Route path="my-lab-orders" element={<MyLabOrdersPage />} />
              </Route>

              <Route element={<RequireCapability capability="prescriptions.prescribe" />}>
                <Route path="rx/new" element={<PrescribePage />} />
              </Route>
              <Route element={<RequireCapability capability="treatment_plans.view" />}>
                <Route path="rx/reviews" element={<PlanReviewsPage />} />
              </Route>
              <Route element={<RequireCapability capability="self.medications" />}>
                <Route path="my-medications" element={<MyMedicationsPage />} />
                <Route path="my-treatment-plans" element={<MyTreatmentPlansPage />} />
              </Route>

              <Route element={<RequireCapability capability="users.manage" />}>
                <Route path="admin/users" element={<UsersPage />} />
                <Route path="admin/users/new" element={<UserCreatePage />} />
                <Route path="admin/users/:id" element={<UserDetailPage />} />
              </Route>
              <Route element={<RequireCapability capability="audit.view" />}>
                <Route path="admin/audit-logs" element={<AuditLogsPage />} />
              </Route>
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
