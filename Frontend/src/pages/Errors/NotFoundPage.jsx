import { Link } from 'react-router-dom'
import { EmptyState } from '../../components/ui/Feedback'
import { InfoIcon } from '../../components/ui/icons'
import Panel from '../../components/ui/Panel'

export default function NotFoundPage() {
  return (
    <Panel>
      <EmptyState icon={InfoIcon} title="Page not found">
        This page does not exist or has moved. <Link to="/">Go to your dashboard</Link>
      </EmptyState>
    </Panel>
  )
}
