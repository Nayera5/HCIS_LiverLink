import { useEffect, useId, useRef, useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import { createDrug, searchDrugs } from '../../api/prescriptions'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { ROUTE_OPTIONS } from './rxFormat'

/** Inline form to add a missing drug to the catalog (drugs.manage). */
function AddDrugForm({ initialName, onCreated, onCancel }) {
  const [form, setForm] = useState({ name: initialName, generic_name: '', drug_class: '', default_route: '', common_dose: '' })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const set = (key) => (event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))

  const save = async () => {
    if (!form.name.trim()) {
      setErrors({ name: 'Enter the drug name.' })
      return
    }
    setSaving(true)
    setErrors({})
    try {
      onCreated(await createDrug({ ...form, name: form.name.trim() }))
    } catch (err) {
      const fields = fieldErrors(err)
      setErrors(Object.keys(fields).length ? fields : { form: getErrorMessage(err, 'Could not add the drug.') })
      setSaving(false)
    }
  }

  // A <div>, not a nested <form>: this sits inside the prescription form.
  return (
    <div className="rx-add-drug" role="group" aria-label="Add a drug to the catalog">
      <p className="cell-primary">Add a drug to the catalog</p>
      {errors.form && <Alert variant="error">{errors.form}</Alert>}
      <div className="rx-grid">
        <TextField label="Name" value={form.name} onChange={set('name')} error={errors.name} />
        <TextField label="Generic name (optional)" value={form.generic_name} onChange={set('generic_name')} />
        <TextField label="Class (optional)" value={form.drug_class} onChange={set('drug_class')}
          placeholder="e.g. Antiviral (HBV)" />
        <SelectField label="Usual route" optional placeholder="—" options={ROUTE_OPTIONS}
          value={form.default_route} onChange={set('default_route')} />
        <TextField label="Usual dose (optional)" value={form.common_dose} onChange={set('common_dose')}
          placeholder="e.g. 300 mg once daily" />
      </div>
      <div className="inline-actions">
        <Button variant="secondary" size="sm" onClick={onCancel}>Cancel</Button>
        <Button size="sm" loading={saving} onClick={save}>Add drug</Button>
      </div>
    </div>
  )
}

/**
 * Accessible combobox over the drug catalog. `value` is the chosen drug object (or null).
 * Users with drugs.manage can add a drug that is not in the list.
 */
export default function DrugAutocomplete({ value, onChange, error }) {
  const { can } = useAuth()
  const id = useId()
  const listId = `${id}-list`
  const [text, setText] = useState(value?.name || '')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const [searchError, setSearchError] = useState('')
  const [adding, setAdding] = useState(false)
  const requestRef = useRef(0)

  useEffect(() => {
    const term = text.trim()
    if (!open || term.length < 2 || (value && value.name === text)) return undefined
    const ticket = ++requestRef.current
    const timer = setTimeout(() => {
      searchDrugs({ q: term }).then(
        (data) => {
          if (ticket !== requestRef.current) return
          setResults(data)
          setActive(data.length ? 0 : -1)
          setSearchError('')
        },
        (err) => ticket === requestRef.current && setSearchError(getErrorMessage(err, 'Could not search drugs.')),
      )
    }, 200)
    return () => clearTimeout(timer)
  }, [text, open, value])

  const choose = (drug) => {
    onChange(drug)
    setText(drug.name)
    setOpen(false)
    setResults([])
  }

  const onKeyDown = (event) => {
    if (!open || !results.length) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActive((i) => (i + 1) % results.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActive((i) => (i <= 0 ? results.length - 1 : i - 1))
    } else if (event.key === 'Enter' && active >= 0) {
      event.preventDefault()
      choose(results[active])
    } else if (event.key === 'Escape') {
      setOpen(false)
    }
  }

  const term = text.trim()
  const exact = results.some((d) => d.name.toLowerCase() === term.toLowerCase())
  const showList = open && term.length >= 2 && !(value && value.name === text)

  return (
    <div className="rx-combobox">
      <TextField
        label="Drug"
        value={text}
        error={error || searchError}
        hint={value ? [value.code, value.drug_class, value.common_dose && `usual: ${value.common_dose}`].filter(Boolean).join(' · ')
          : 'Type at least 2 letters of the name, generic name or class.'}
        role="combobox"
        autoComplete="off"
        aria-autocomplete="list"
        aria-expanded={showList}
        aria-controls={listId}
        aria-activedescendant={showList && active >= 0 ? `${listId}-${active}` : undefined}
        onChange={(event) => {
          setText(event.target.value)
          setOpen(true)
          if (value) onChange(null)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={onKeyDown}
      />
      {showList && (
        <ul id={listId} role="listbox" className="rx-combobox__list">
          {results.map((drug, index) => (
            <li key={drug.id} id={`${listId}-${index}`} role="option" aria-selected={index === active}
              className={`rx-combobox__option ${index === active ? 'rx-combobox__option--active' : ''}`}
              onMouseDown={(event) => { event.preventDefault(); choose(drug) }}>
              <span className="cell-primary">{drug.name}</span>
              <span className="cell-secondary">{[drug.generic_name, drug.drug_class].filter(Boolean).join(' · ')}</span>
            </li>
          ))}
          {!results.length && <li className="rx-combobox__empty">No matching drug in the catalog.</li>}
          {can('drugs.manage') && !exact && (
            <li className="rx-combobox__add">
              <Button variant="link" size="sm" onMouseDown={(event) => { event.preventDefault(); setAdding(true); setOpen(false) }}>
                + Add “{term}” to the catalog
              </Button>
            </li>
          )}
        </ul>
      )}
      {adding && (
        <AddDrugForm initialName={term} onCancel={() => setAdding(false)}
          onCreated={(drug) => { setAdding(false); choose(drug) }} />
      )}
    </div>
  )
}
