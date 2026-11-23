import { forwardRef, useId } from 'react'
import './ui.css'

/** Labelled multi-line input matching TextField (label, hint, error). */
const TextAreaField = forwardRef(function TextAreaField(
  { label, error, hint, id, className = '', optional = false, rows = 3, ...props },
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
          {optional && <span className="field__optional">(optional)</span>}
        </label>
      </div>
      <div className="field__control">
        <textarea
          ref={ref}
          id={inputId}
          rows={rows}
          className="field__input field__textarea"
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={describedBy}
          {...props}
        />
      </div>
      {hint && !error && <p id={hintId} className="field__hint">{hint}</p>}
      {error && <p id={errorId} className="field__error">{error}</p>}
    </div>
  )
})

export default TextAreaField
