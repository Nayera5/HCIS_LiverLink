import { useCallback } from 'react'
import { listPatients } from '../../api/patients'
import SelectField from '../../components/ui/SelectField'
import { useApi } from '../../hooks/useApi'
import { patientName } from '../Patients/patientDisplay'

const PAGE_SIZE = 100

/**
 * Dropdown of all registered patients (patients.view), ordered by name.
 * `value` is the chosen patient ({ id, mrn, ... }) or null; `onChange` receives it.
 *
 * Note: only the first 100 patients (by last name) are loaded. If the registry grows past
 * that, switch this back to a search-based picker instead of raising the page size further.
 */
export default function PatientPicker({ value, onChange, error }) {
  const loader = useCallback(() => listPatients({ ordering: 'last_name', page_size: PAGE_SIZE }), [])
  const { data, loading, error: loadError } = useApi(loader)

  const patients = data?.results || []
  const options = patients.map((patient) => ({ value: String(patient.id), label: `${patientName(patient)} — ${patient.mrn}` }))

  return (
    <SelectField
      label="Patient"
      name="patient"
      placeholder={loading ? 'Loading patients…' : 'Choose a patient'}
      options={options}
      value={value ? String(value.id) : ''}
      disabled={loading}
      error={error || (loadError ? 'Could not load the patient list.' : '')}
      onChange={(event) => {
        const selected = patients.find((patient) => String(patient.id) === event.target.value) || null
        onChange(selected)
      }}
    />
  )
}
