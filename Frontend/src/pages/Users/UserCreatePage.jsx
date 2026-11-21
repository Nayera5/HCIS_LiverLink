import { useNavigate } from 'react-router-dom'
import { createStaffAccount } from '../../api/users'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import StaffAccountForm from './StaffAccountForm'
import './Users.css'

export default function UserCreatePage() {
  const navigate = useNavigate()

  const create = async (payload) => {
    const account = await createStaffAccount(payload)
    navigate(`/admin/users/${account.id}`, { state: { flash: `Account "${account.username}" was created.` } })
  }

  return (
    <>
      <PageHeader back={{ to: '/admin/users', label: 'Users & access' }} eyebrow="Administration"
        title="New staff account" />
      <Panel title="Account details"
        subtitle="Staff accounts are created by the administrator. Patients and donors register themselves or through the coordinator.">
        <StaffAccountForm creating submitLabel="Create account" onSubmit={create}
          onCancel={() => navigate('/admin/users')} />
      </Panel>
    </>
  )
}
