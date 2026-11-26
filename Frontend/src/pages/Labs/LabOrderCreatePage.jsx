import { useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import { createLabOrder, listLabTests } from '../../api/labs'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { LoadingBlock } from '../../components/ui/Feedback'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import { useApi } from '../../hooks/useApi'
import { PRIORITY_OPTIONS } from './labDisplay'
import { rangeText } from './labFormat'
import './Labs.css'

export function LabOrderForm({ patient, encounter, onCreated, onCancel }) {
  const { data: tests, error: testsError, loading } = useApi(listLabTests)
  const [priority, setPriority] = useState('routine')
  const [selected, setSelected] = useState(() => new Set())
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const toggle = (id) => setSelected((prev) => {
    const next = new Set(prev)
    if (!next.delete(id)) next.add(id)
    return next
  })

  const submit = async (event) => {
    event.preventDefault()
    if (!selected.size) {
      setError('Select at least one test.')
      return
    }
    setError('')
    setSaving(true)
    try {
      const order = await createLabOrder({
        patient: patient.id, encounter: encounter.encounter_id, priority, tests: [...selected],
      })
      onCreated(order)
    } catch (err) {
      const fields = fieldErrors(err)
      setError(fields.tests || fields.patient || fields.encounter || fields.form
        || getErrorMessage(err, 'Could not place the order.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading && !tests) {
    return (
      <div className="content-stack">
        <LoadingBlock label="Loading tests" />
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
      </div>
    )
  }
  if (testsError) {
    return (
      <div className="content-stack">
        <Alert variant="error">{getErrorMessage(testsError, 'Could not load the test catalog.')}</Alert>
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
      </div>
    )
  }

  return (
    <form onSubmit={submit} noValidate className="content-stack">
      {error && <Alert variant="error">{error}</Alert>}
      <Panel title="Tests" subtitle="Tick every test to include in this order.">
        <fieldset className="test-grid">
          <legend className="visually-hidden">Tests</legend>
          {tests.map((test) => (
            <label key={test.id} className={`test-option ${selected.has(test.id) ? 'test-option--on' : ''}`}>
              <input type="checkbox" checked={selected.has(test.id)} onChange={() => toggle(test.id)} />
              <span>
                <span className="cell-primary">{test.name}</span>
                <span className="cell-secondary">
                  {test.unit || 'no unit'} · normal {rangeText(test.normal_min, test.normal_max)}
                </span>
              </span>
            </label>
          ))}
        </fieldset>
      </Panel>
      <Panel title="Priority">
        <SelectField label="Priority" options={PRIORITY_OPTIONS} value={priority}
          onChange={(event) => setPriority(event.target.value)} />
      </Panel>
      <div className="form-actions">
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button type="submit" loading={saving}>
          Place order{selected.size ? ` (${selected.size} test${selected.size === 1 ? '' : 's'})` : ''}
        </Button>
      </div>
    </form>
  )
}
