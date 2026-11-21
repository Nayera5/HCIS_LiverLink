import Badge from '../../components/ui/Badge'

export const CATEGORY_LABELS = {
  liver_patient: 'Liver patient',
  recipient: 'Recipient',
  donor: 'Living donor',
}

export const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS).map(([value, label]) => ({ value, label }))

export const SEX_OPTIONS = [
  { value: 'female', label: 'Female' },
  { value: 'male', label: 'Male' },
]

export const BLOOD_GROUP_OPTIONS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].map((value) => ({
  value,
  label: value,
}))

// Colours follow the dashboard design reference (Recipient teal, Living donor purple).
const CATEGORY_TONES = { liver_patient: 'neutral', recipient: 'teal', donor: 'purple' }

export function categoryBadge(category) {
  return <Badge tone={CATEGORY_TONES[category] || 'neutral'}>{CATEGORY_LABELS[category] || category}</Badge>
}

/** "54 M" / "61 F" as in the design reference. */
export function ageSex(patient) {
  const sex = patient.sex === 'female' ? 'F' : patient.sex === 'male' ? 'M' : ''
  return [patient.age, sex].filter((part) => part !== undefined && part !== null && part !== '').join(' ')
}

export function patientName(patient) {
  return patient.full_name || [patient.first_name, patient.last_name].filter(Boolean).join(' ')
}
