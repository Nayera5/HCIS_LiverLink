import { useCallback, useState } from 'react'
import { useLocation, useParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { getUser, setUserActive, updateUser } from '../../api/users'
import { useAuth } from '../../auth/authContext'
import { ROLE_LABELS } from '../../auth/roles'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { ConfirmDialog, LoadingBlock } from '../../components/ui/Feedback'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { accountBadge, accountTitle } from './accountStatus'
import StaffAccountForm from './StaffAccountForm'
import './Users.css'

export default function UserDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const { user: me } = useAuth()
  const loader = useCallback(() => getUser(id), [id])
  const { data: account, error, loading, setData } = useApi(loader)
  const [flash, setFlash] = useState(location.state?.flash || '')
  const [confirming, setConfirming] = useState(false)
  const [toggling, setToggling] = useState(false)
  const [actionError, setActionError] = useState('')
  const [formKey, setFormKey] = useState(0)

  if (loading && !account) return <LoadingBlock label="Loading account" />
  if (error && !account) {
    return (
      <>
        <PageHeader back={{ to: '/admin/users', label: 'Users & access' }} title="Account" />
        <Alert variant="error">{getErrorMessage(error, 'Could not load this account.')}</Alert>
      </>
    )
  }

  const isSelf = account.id === me.id
  const isPatient = account.role === 'patient'
  // Only a Django superuser may change a superuser account (the backend enforces this too).
  const superuserLocked = account.is_superuser && !me.is_superuser
  const canEdit = !isPatient && !superuserLocked

  const save = async (payload) => {
    const updated = await updateUser(account.id, payload)
    setData(updated)
    setFormKey((k) => k + 1)
    setFlash('Changes saved.')
  }

  const toggleActive = async () => {
    setToggling(true)
    setActionError('')
    try {
      const updated = await setUserActive(account.id, !account.is_active)
      setData(updated)
      setFlash(updated.is_active ? 'Account activated.' : 'Account deactivated. The user has been signed out.')
      setConfirming(false)
    } catch (err) {
      setActionError(getErrorMessage(err, 'Could not change the account status.'))
      setConfirming(false)
    } finally {
      setToggling(false)
    }
  }

  return (
    <>
      <PageHeader
        back={{ to: '/admin/users', label: 'Users & access' }}
        eyebrow={`@${account.username} · ${accountTitle(account)}`}
        title={account.full_name || account.username}
      />
      <div className="account-summary">
        {accountBadge(account)}
        <Badge tone="info">{ROLE_LABELS[account.role]}</Badge>
        {account.is_superuser && <Badge tone="purple">Django superuser</Badge>}
        {isSelf && <Badge tone="teal">This is you</Badge>}
      </div>

      <div className="content-stack detail-page">
        {flash && <Alert variant="success">{flash}</Alert>}
        {actionError && <Alert variant="error">{actionError}</Alert>}

        <div className="content-grid">
          <Panel title="Account details" subtitle={canEdit ? 'Name, contact and role in LiverLink' : undefined}>
            {canEdit ? (
              <StaffAccountForm
                key={formKey}
                initial={{
                  first_name: account.first_name, last_name: account.last_name, email: account.email || '',
                  job_title: account.job_title || '', department: account.department || '',
                  license_no: account.license_no || '', phone: account.phone || '',
                }}
                lockJobTitle={isSelf}
                submitLabel={account.has_staff_profile ? 'Save changes' : 'Save and assign job title'}
                onSubmit={save}
              />
            ) : (
              <>
                <dl className="detail-list">
                  <div><dt>Name</dt><dd>{account.full_name || '—'}</dd></div>
                  <div><dt>Username</dt><dd>{account.username}</dd></div>
                  <div><dt>Email</dt><dd>{account.email || '—'}</dd></div>
                  <div><dt>Role</dt><dd>{ROLE_LABELS[account.role]}</dd></div>
                </dl>
                <p className="muted-text panel-note">
                  {isPatient
                    ? 'Patient and donor details are managed in the patient registry. Here you can only activate or deactivate the account.'
                    : 'Only a Django superuser can edit a superuser account.'}
                </p>
              </>
            )}
          </Panel>

          <div className="content-stack">
            <Panel title="Access">
              <div className="access-row">
                <p className="muted-text">
                  {account.is_active
                    ? 'This account can sign in.'
                    : 'This account cannot sign in. Its records are kept.'}
                </p>
                {!isSelf && !superuserLocked && (
                  <Button variant={account.is_active ? 'secondary' : 'primary'} size="sm"
                    onClick={() => (account.is_active ? setConfirming(true) : toggleActive())} loading={toggling}>
                    {account.is_active ? 'Deactivate' : 'Activate'}
                  </Button>
                )}
              </div>
              {isSelf && <p className="muted-text panel-note">You cannot deactivate your own account.</p>}
            </Panel>

            <Panel title="Activity">
              <dl className="detail-list">
                <div><dt>Last sign-in</dt><dd>{account.last_login ? formatDateTime(account.last_login) : 'Never'}</dd></div>
                <div><dt>Created</dt><dd>{formatDateTime(account.date_joined)}</dd></div>
              </dl>
            </Panel>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={confirming}
        title={`Deactivate ${account.full_name || account.username}?`}
        confirmLabel="Deactivate"
        tone="danger"
        busy={toggling}
        onConfirm={toggleActive}
        onCancel={() => setConfirming(false)}
      >
        They will be signed out everywhere and cannot sign in until the account is activated again.
        Their records are kept.
      </ConfirmDialog>
    </>
  )
}

