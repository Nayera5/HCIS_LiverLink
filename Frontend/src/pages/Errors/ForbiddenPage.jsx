import { Link } from 'react-router-dom'
import { EmptyState } from '../../components/ui/Feedback'
import { ShieldIcon } from '../../components/ui/icons'
import Panel from '../../components/ui/Panel'

export default function ForbiddenPage() {
  return (
    <Panel>
      <EmptyState icon={ShieldIcon} title="You do not have access to this page">
        Your role and job title do not include this feature. If you think this is a mistake,
        contact the system administrator. <Link to="/">Go to your dashboard</Link>
      </EmptyState>
    </Panel>
  )
}
