import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { listAppointments } from '../../api/scheduling'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { ClockIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { AppointmentTable } from '../Appointments/appointmentParts'
import { replaceRow, splitUpcoming } from '../Appointments/appointmentRules'

/**
 * Portal: own appointments (self.appointments). The backend returns only the signed-in patient's
 * visits. Booked visits can be rescheduled or cancelled here.
 */
export default function MyAppointmentsPage() {
  const { can } = useAuth()
  const location = useLocation()
  const [flash] = useState(location.state?.flash || '')
  const { data, error, loading, setData } = useApi(listAppointments)
  const { upcoming, past } = splitUpcoming(data || [])
  const who = { can, portal: true }
  const onChanged = (updated) => setData(replaceRow(data, updated))

  return (
    <>
      <PageHeader eyebrow="Patient portal" title="My appointments"
        actions={<Button as={Link} to="/my-appointments/new">Book appointment</Button>} />
      {flash && <Alert variant="success" className="form-alert">{flash}</Alert>}
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load your appointments.')}</Alert>}
      {loading && !data ? <LoadingBlock label="Loading appointments" /> : (
        <div className="content-stack">
          <Panel title="Upcoming" flush={upcoming.length > 0}>
            {upcoming.length ? (
              <AppointmentTable appointments={upcoming} who={who} onChanged={onChanged} showDate showPatient={false} />
            ) : (
              <EmptyState icon={ClockIcon} title="No upcoming appointments">
                Book a visit with your doctor using the button above.
              </EmptyState>
            )}
          </Panel>
          {past.length > 0 && (
            <Panel title="Past and cancelled" flush>
              <AppointmentTable appointments={past} who={who} onChanged={onChanged} showDate showPatient={false} />
            </Panel>
          )}
        </div>
      )}
    </>
  )
}
