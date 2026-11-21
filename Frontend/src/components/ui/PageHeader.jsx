import { Link } from 'react-router-dom'
import { ChevronLeftIcon } from './icons'
import './ui.css'

/** Page title block: small context line, large title, actions on the right. */
export default function PageHeader({ eyebrow, title, actions, back }) {
  return (
    <>
      {back && (
        <Link className="page-back" to={back.to}>
          <ChevronLeftIcon size={16} />
          {back.label}
        </Link>
      )}
      <div className="page-header">
        <div>
          {eyebrow && <p className="page-header__eyebrow">{eyebrow}</p>}
          <h1 className="page-header__title">{title}</h1>
        </div>
        {actions && <div className="page-header__actions">{actions}</div>}
      </div>
    </>
  )
}
