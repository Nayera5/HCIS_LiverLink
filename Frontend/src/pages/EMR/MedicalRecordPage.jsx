import { useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { getPatient } from '../../api/patients'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import { LoadingBlock } from '../../components/ui/Feedback'
import PageHeader from '../../components/ui/PageHeader'
import { useApi } from '../../hooks/useApi'
import { ageSex, categoryBadge, patientName } from '../Patients/patientDisplay'
import { ImagingOrdersPanel } from '../Imaging/imagingParts'
import { PatientImagingReportsPanel } from '../Reports/reportPanels'
import { DocumentsPanel, EncountersPanel, HistoryPanel } from './emrPanels'
import '../Patients/Patients.css'

/**
 * Staff: one patient's medical record (emr.view). Doctors (emr.write) can add history,
 * start encounters and upload/release documents; everyone else reads.
 */
export default function MedicalRecordPage() {
  const { id } = useParams()
  const { can } = useAuth()
  const canEdit = can('emr.write')
  const loader = useCallback(() => getPatient(id), [id])
  const { data: patient, error, loading } = useApi(loader)
  const back = { to: `/patients/${id}`, label: 'Patient profile' }

  if (loading && !patient) return <LoadingBlock label="Loading medical record" />
  if (error && !patient) {
    return (
      <>
        <PageHeader back={back} title="Medical record" />
        <Alert variant="error">{getErrorMessage(error, 'Could not load this patient.')}</Alert>
      </>
    )
  }

  return (
    <>
      <PageHeader back={back} eyebrow="Medical record" title={patientName(patient)} />
      <div className="patient-summary">
        <span className="patient-summary__mrn">{patient.mrn}</span>
        <span className="muted-text">· {ageSex(patient)}</span>
        {categoryBadge(patient.category)}
      </div>
      {!canEdit && (
        <Alert variant="info" className="form-alert">
          You can view this record. Only hepatologists and transplant surgeons can change it.
        </Alert>
      )}
      <div className="content-grid">
        <div className="content-stack">
          <EncountersPanel patientId={patient.id} canCreate={canEdit} encounterLink={(encId) => `/encounters/${encId}`} />
          {can('imaging.view') && <ImagingOrdersPanel patientId={patient.id} canOrder={false} />}
          <DocumentsPanel patientId={patient.id} canEdit={canEdit} />
        </div>
        <div className="content-stack">
          <HistoryPanel patientId={patient.id} canEdit={canEdit} />
          {can('reports.imaging_patient') && <PatientImagingReportsPanel />}
        </div>
      </div>
    </>
  )
}
