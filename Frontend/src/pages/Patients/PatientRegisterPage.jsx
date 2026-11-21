import { useNavigate } from 'react-router-dom'
import { registerPatient } from '../../api/patients'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import PatientForm from './PatientForm'
import './Patients.css'

/** Staff registration: creates a hospital record (MRN) without a portal account. */
export default function PatientRegisterPage() {
  const navigate = useNavigate()

  const register = async (payload) => {
    const patient = await registerPatient(payload)
    navigate(`/patients/${patient.id}`, {
      state: { flash: `${patient.first_name} ${patient.last_name} was registered with MRN ${patient.mrn}.` },
    })
  }

  return (
    <>
      <PageHeader back={{ to: '/patients', label: 'Patients' }} eyebrow="Patient & donor registry"
        title="Register patient" />
      <Panel title="Patient details"
        subtitle="The MRN is generated automatically when you save. This creates a hospital record only; patients who want portal access register their own account.">
        <PatientForm withCategory submitLabel="Register patient" onSubmit={register}
          onCancel={() => navigate('/patients')} />
      </Panel>
    </>
  )
}
