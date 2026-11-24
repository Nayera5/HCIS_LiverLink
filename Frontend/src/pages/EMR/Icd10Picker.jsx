import { useEffect, useId, useRef, useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { searchIcd10 } from '../../api/emr'
import TextField from '../../components/ui/TextField'
import '../Prescriptions/Prescriptions.css' // rx-combobox styles (same dropdown as the drug search)

const FIELDS = [
  { key: 'description', label: 'Diagnosis', hint: 'Search by name, for example cirrhosis or HCC.' },
  { key: 'code', label: 'ICD-10 code', hint: 'Search by code, for example C22.' },
]

/**
 * Two linked search boxes over the ICD-10 catalog: choosing from either one fills both.
 * `value` is the chosen { code, description } or null; typing again clears the choice.
 */
export default function Icd10Picker({ value, onChange, error }) {
  const id = useId()
  const [query, setQuery] = useState({ field: '', text: '' }) // what is being typed, and in which box
  const [results, setResults] = useState(null) // null = not searched yet
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const [searchError, setSearchError] = useState('')
  const requestRef = useRef(0)

  const term = query.text.trim()
  const listId = `${id}-list`
  const optionId = (index) => `${listId}-${index}`

  useEffect(() => {
    const ticket = ++requestRef.current // ignore answers to older searches
    if (term.length < 2) return undefined
    const timer = setTimeout(() => {
      searchIcd10(term).then(
        (data) => ticket === requestRef.current && setResults(data),
        (err) => ticket === requestRef.current && setSearchError(getErrorMessage(err, 'Could not search the ICD-10 list.')),
      )
    }, 200)
    return () => clearTimeout(timer)
  }, [term])

  const type = (field, text) => {
    setQuery({ field, text })
    if (text.trim() !== term) {
      setResults(null)
      setSearchError('')
    }
    setActive(0)
    setOpen(true)
    if (value) onChange(null)
  }

  const choose = (item) => {
    onChange(item)
    setQuery({ field: '', text: '' })
    setResults(null)
    setOpen(false)
  }

  const move = (index) => {
    setActive(index)
    document.getElementById(optionId(index))?.scrollIntoView({ block: 'nearest' })
  }

  const onKeyDown = (event) => {
    if (event.key === 'Escape') setOpen(false)
    if (!open || !results?.length) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      move((active + 1) % results.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      move((active || results.length) - 1)
    } else if (event.key === 'Enter') {
      event.preventDefault()
      choose(results[active])
    }
  }

  return (
    <div className="form-stack">
      {FIELDS.map(({ key, label, hint }) => {
        const showList = open && query.field === key && term.length >= 2 && results !== null
        return (
          <div key={key} className="rx-combobox">
            <TextField
              label={label}
              hint={hint}
              error={(query.field === key && searchError) || (key === 'description' && error)}
              value={value ? value[key] : query.field === key ? query.text : ''}
              title={value ? value[key] : undefined}
              role="combobox"
              autoComplete="off"
              aria-autocomplete="list"
              aria-expanded={showList}
              aria-controls={listId}
              aria-activedescendant={showList && results.length ? optionId(active) : undefined}
              onChange={(event) => type(key, event.target.value)}
              onFocus={() => setOpen(true)}
              onBlur={() => setOpen(false)}
              onKeyDown={onKeyDown}
            />
            {showList && (
              <ul id={listId} role="listbox" aria-label={label} className="rx-combobox__list"
                onMouseDown={(event) => event.preventDefault() /* keep focus in the box */}>
                {results.map((item, index) => (
                  <li key={item.code} id={optionId(index)} role="option" aria-selected={index === active}
                    className={`rx-combobox__option ${index === active ? 'rx-combobox__option--active' : ''}`}
                    onClick={() => choose(item)}>
                    <span className="cell-primary"><span className="emr-code">{item.code}</span> {item.description}</span>
                  </li>
                ))}
                {!results.length && <li className="rx-combobox__empty">No matching diagnosis in the ICD-10 list.</li>}
              </ul>
            )}
          </div>
        )
      })}
    </div>
  )
}
