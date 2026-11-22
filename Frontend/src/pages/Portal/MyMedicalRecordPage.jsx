import PageHeader from '../../components/ui/PageHeader'
import { DocumentsPanel, EncountersPanel, HistoryPanel } from '../EMR/emrPanels'
import '../Patients/Patients.css'

/**
 * Portal: own medical record, read-only (self.medical_records). The backend only returns the
 * signed-in patient's signed encounters, their medical history and released documents.
 */
export default function MyMedicalRecordPage() {
  return (
    <>
      <PageHeader eyebrow="Patient portal" title="My medical record" />
      <p className="muted-text form-alert">
        This is a read-only copy of your record. If something looks wrong, please tell your care team.
      </p>
      <div className="content-grid">
        <div className="content-stack">
          <EncountersPanel encounterLink={(id) => `/my-medical-record/encounters/${id}`} />
          <DocumentsPanel />
        </div>
        <div className="content-stack">
          <HistoryPanel />
        </div>
      </div>
    </>
  )
}
