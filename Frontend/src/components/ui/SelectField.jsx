import { forwardRef, useId } from 'react'
import './ui.css'

/**
 * Labelled <select> matching TextField.
 * options: [{ value, label }] or groups: [{ group, options: [{ value, label }] }]
 */
const SelectField = forwardRef(function SelectField(
  { label, error, hint, options = [], placeholder, id, className = '', optional = false, ...selectProps },
  ref,
) {
  const autoId = useId()
  const selectId = id || autoId
  const errorId = `${selectId}-error`
  const hintId = `${selectId}-hint`
  const describedBy = [error && errorId, hint && hintId].filter(Boolean).join(' ') || undefined

  const renderOption = (option) => (
    <option key={option.value} value={option.value}>
      {option.label}
    </option>
  )

  return (
    <div className={`field ${error ? 'field--invalid' : ''} ${className}`}>
      {label && (
        <div className="field__label-row">
          <label className="field__label" htmlFor={selectId}>
            {label}
            {optional && <span className="field__optional">(optional)</span>}
          </label>
        </div>
      )}
      <div className="field__control">
        <select
          ref={ref}
          id={selectId}
          className="field__input field__select"
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={describedBy}
          {...selectProps}
        >
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((item) =>
            item.group ? (
              <optgroup key={item.group} label={item.group}>
                {item.options.map(renderOption)}
              </optgroup>
            ) : (
              renderOption(item)
            ),
          )}
        </select>
      </div>
      {hint && !error && (
        <p id={hintId} className="field__hint">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="field__error">
          {error}
        </p>
      )}
    </div>
  )
})

export default SelectField
