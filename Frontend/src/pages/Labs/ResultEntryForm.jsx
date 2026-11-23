import { useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import { enterLabResult } from '../../api/labs'
import Button from '../../components/ui/Button'

/**
 * Inline form to type in a value received from the external lab (or correct one).
 * `onSaved(result)` gets the updated LabResult from the server (flag already computed).
 */
export default function ResultEntryForm({ result, onSaved, onCancel }) {
  const [value, setValue] = useState(result.value === null ? '' : String(Number(result.value)))
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    const text = value.trim()
    if (text === '' || Number.isNaN(Number(text)) || Number(text) < 0) {
      setError('Enter a number of 0 or more.')
      return
    }
    setError('')
    setSaving(true)
    try {
      onSaved(await enterLabResult(result.id, text))
    } catch (err) {
      const fields = fieldErrors(err)
      setError(fields.value || fields.form || getErrorMessage(err, 'Could not save the result.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="result-entry" onSubmit={submit} noValidate>
      <div className="result-entry__row">
        <input className="field__input result-entry__input" type="number" step="any" min="0" inputMode="decimal"
          aria-label={`${result.test_name} value${result.unit ? ` in ${result.unit}` : ''}`}
          aria-invalid={error ? 'true' : undefined} value={value} placeholder={result.unit || 'Value'}
          onChange={(event) => { setValue(event.target.value); setError('') }} />
        <Button type="submit" size="sm" loading={saving}>Save</Button>
        {onCancel && <Button variant="secondary" size="sm" onClick={onCancel} disabled={saving}>Cancel</Button>}
      </div>
      {error && <p className="field__error" role="alert">{error}</p>}
    </form>
  )
}
