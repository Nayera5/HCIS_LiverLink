import { forwardRef, useState } from 'react'
import TextField from './TextField'
import { EyeIcon, EyeOffIcon } from './icons'

/** TextField for passwords, with a show/hide toggle. */
const PasswordField = forwardRef(function PasswordField(props, ref) {
  const [visible, setVisible] = useState(false)

  return (
    <TextField
      ref={ref}
      {...props}
      type={visible ? 'text' : 'password'}
      endAdornment={
        <button
          type="button"
          className="field__icon-button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? 'Hide password' : 'Show password'}
          aria-pressed={visible}
          disabled={props.disabled}
        >
          {visible ? <EyeOffIcon /> : <EyeIcon />}
        </button>
      }
    />
  )
})

export default PasswordField
