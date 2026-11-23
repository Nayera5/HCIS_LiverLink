import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AuthProvider from './auth/AuthProvider'
import { PublicOnly, RequireAuth, RequireCapability } from './auth/guards'
import AppShell from './components/layout/AppShell'
import AppointmentsPage from './pages/Appointments/AppointmentsPage'
import BookAppointmentPage from './pages/Appointments/BookAppointmentPage'
import SchedulePage from './pages/Appointments/SchedulePage'
import AuditLogsPage from './pages/AuditLogs/AuditLogsPage'
import ForgotPasswordPage from './pages/Auth/ForgotPasswordPage'
import RegisterPage from './pages/Auth/RegisterPage'
import ResetPasswordPage from './pages/Auth/ResetPasswordPage'
import InvoiceCreatePage from './pages/Billing/InvoiceCreatePage'
import InvoiceDetailPage from './pages/Billing/InvoiceDetailPage'
import InvoicesPage from './pages/Billing/InvoicesPage'
import ServiceCatalogPage from './pages/Billing/ServiceCatalogPage'
import DashboardPage from './pages/Dashboard/DashboardPage'
import DonorApplicationCreatePage from './pages/DonorApplications/DonorApplicationCreatePage'
import DonorApplicationDetailPage from './pages/DonorApplications/DonorApplicationDetailPage'
import DonorApplicationsPage from './pages/DonorApplications/DonorApplicationsPage'
import EncounterPage from './pages/EMR/EncounterPage'
import MedicalRecordPage from './pages/EMR/MedicalRecordPage'
import NotFoundPage from './pages/Errors/NotFoundPage'
import LoginRoute from './pages/Login/LoginRoute'
import NotificationsPage from './pages/Notifications/NotificationsPage'
import PatientDetailPage from './pages/Patients/PatientDetailPage'
import PatientRegisterPage from './pages/Patients/PatientRegisterPage'
import PatientsPage from './pages/Patients/PatientsPage'
import MyAppointmentsPage from './pages/Portal/MyAppointmentsPage'
import MyConsentsPage from './pages/Portal/MyConsentsPage'
import MyDonorApplicationsPage from './pages/Portal/MyDonorApplicationsPage'
import MyMedicalRecordPage from './pages/Portal/MyMedicalRecordPage'
import MyInvoiceDetailPage from './pages/Portal/MyInvoiceDetailPage'
import MyInvoicesPage from './pages/Portal/MyInvoicesPage'
import MyRecordPage from './pages/Portal/MyRecordPage'
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
              <Route path="notifications" element={<NotificationsPage />} />

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
              <Route element={<RequireCapability capability="self.donor_applications" />}>
                <Route path="my-donor-applications" element={<MyDonorApplicationsPage />} />
              </Route>
              <Route element={<RequireCapability capability="self.invoices" />}>
                <Route path="my-invoices" element={<MyInvoicesPage />} />
                <Route path="my-invoices/:id" element={<MyInvoiceDetailPage />} />
               </Route>
              <Route element={<RequireCapability capability="self.consents" />}>
                <Route path="my-consents" element={<MyConsentsPage />} />
              </Route>
              <Route element={<RequireCapability capability="self.medical_records" />}>
                <Route path="my-medical-record" element={<MyMedicalRecordPage />} />
                <Route path="my-medical-record/encounters/:id" element={<EncounterPage portal />} />
              </Route>

              <Route element={<RequireCapability capability="self.appointments" />}>
                <Route path="my-appointments" element={<MyAppointmentsPage />} />
                <Route path="my-appointments/new" element={<BookAppointmentPage />} />
              </Route>

              <Route element={<RequireCapability capability="appointments.view" />}>
                <Route path="appointments" element={<AppointmentsPage />} />
              </Route>
              <Route element={<RequireCapability capability="appointments.book_any" />}>
                <Route path="appointments/new" element={<BookAppointmentPage />} />
              </Route>
              <Route element={<RequireCapability capability={['schedules.manage_own', 'schedules.manage_all']} />}>
                <Route path="schedule" element={<SchedulePage />} />
              </Route>

              <Route element={<RequireCapability capability="emr.view" />}>
                <Route path="patients/:id/medical-record" element={<MedicalRecordPage />} />
                <Route path="encounters/:id" element={<EncounterPage />} />
              </Route>

              <Route element={<RequireCapability capability="donor_applications.view" />}>
                <Route path="donor-applications" element={<DonorApplicationsPage />} />
                <Route path="donor-applications/:id" element={<DonorApplicationDetailPage />} />
              </Route>
              <Route element={<RequireCapability capability="donor_applications.submit_on_behalf" />}>
                <Route path="donor-applications/new" element={<DonorApplicationCreatePage />} />
              </Route>

              <Route element={<RequireCapability capability="billing.view" />}>
                <Route path="billing/services" element={<ServiceCatalogPage />} />
                <Route path="billing/invoices" element={<InvoicesPage />} />
                <Route path="billing/invoices/:id" element={<InvoiceDetailPage />} />
              </Route>
              <Route element={<RequireCapability capability="billing.create_invoice" />}>
                <Route path="billing/invoices/new" element={<InvoiceCreatePage />} />
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
