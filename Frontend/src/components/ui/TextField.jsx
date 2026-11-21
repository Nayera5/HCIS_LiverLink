import { forwardRef, useId } from 'react'
import './ui.css'

/**
 * Labelled text input with an optional action next to the label,
 * an optional trailing element inside the input, and an error message.
 */
const TextField = forwardRef(function TextField(
  { label, labelAction, error, hint, endAdornment, id, className = '', ...inputProps },
  ref,
) {
  const autoId = useId()
  const inputId = id || autoId
  const errorId = `${inputId}-error`
  const hintId = `${inputId}-hint`
  const describedBy = [error && errorId, hint && hintId].filter(Boolean).join(' ') || undefined

  return (
    <div className={`field ${error ? 'field--invalid' : ''} ${className}`}>
      <div className="field__label-row">
        <label className="field__label" htmlFor={inputId}>
          {label}
        </label>
        {labelAction}
      </div>
      <div className="field__control">
        <input
          ref={ref}
          id={inputId}
          className={`field__input ${endAdornment ? 'field__input--with-end' : ''}`}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={describedBy}
          {...inputProps}
        />
        {endAdornment && <div className="field__end">{endAdornment}</div>}
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

export default TextField
