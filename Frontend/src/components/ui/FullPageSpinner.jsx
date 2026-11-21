import { Spinner } from './Feedback'

export default function FullPageSpinner({ label = 'Loading…' }) {
  return (
    <div className="full-page-spinner">
      <Spinner label={label} />
      <span>{label}</span>
    </div>
  )
}
