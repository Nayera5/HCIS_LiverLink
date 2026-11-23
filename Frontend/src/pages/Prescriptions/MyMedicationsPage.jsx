import { useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { getMyMedications } from '../../api/prescriptions'
import Alert from '../../components/ui/Alert'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { PillIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { MedicationTable, MedicationTabs } from './PatientMedicationsPanel'
import './Prescriptions.css'

/** Patient portal: own current and past medications. */
export default function MyMedicationsPage() {
  const { data, error, loading } = useApi(getMyMedications)
  const [tab, setTab] = useState('current')
  const items = data ? data[tab] : []

  return (
    <>
      <PageHeader eyebrow="Patient portal" title="My medications" />
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load your medications.')}</Alert>}
      {loading && !data ? (
        <LoadingBlock label="Loading your medications" />
      ) : data ? (
        <div className="content-stack">
          <Panel>
            <div className="content-stack">
              <MedicationTabs tab={tab} onChange={setTab} counts={{ current: data.current.length, past: data.past.length }} />
              {items.length ? (
                <MedicationTable items={items} />
              ) : (
                <EmptyState icon={PillIcon} title={tab === 'current' ? 'No current medications' : 'No past medications'}>
                  Medications your doctor prescribes appear here.
                </EmptyState>
              )}
            </div>
          </Panel>
          <p className="muted-text panel-note">
            Do not stop or change a medication without talking to your doctor first.
          </p>
        </div>
      ) : null}
    </>
  )
}
