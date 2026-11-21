import { useCallback, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { listUsers } from '../../api/users'
import { JOB_TITLE_LABELS, JOB_TITLE_OPTIONS } from '../../auth/roles'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock, Pagination } from '../../components/ui/Feedback'
import { SearchIcon, UsersIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { accountBadge, accountTitle } from './accountStatus'
import './Users.css'

const PAGE_SIZE = 20
const FILTER_KEYS = ['search', 'role', 'job_title', 'has_staff_profile', 'is_active', 'page']

const ROLE_OPTIONS = [
  { value: 'admin', label: 'Admin' },
  { value: 'clinical_staff', label: 'Clinical staff' },
  { value: 'patient', label: 'Patient / donor' },
]
const STATUS_OPTIONS = [
  { value: 'true', label: 'Active' },
  { value: 'false', label: 'Deactivated' },
]
const TITLE_FILTER_OPTIONS = [
  { value: 'none', label: 'No job title' },
  ...JOB_TITLE_OPTIONS.map(({ group, options }) => ({
    group,
    options: options.map((value) => ({ value, label: JOB_TITLE_LABELS[value] })),
  })),
]

export default function UsersPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = Object.fromEntries(FILTER_KEYS.map((key) => [key, searchParams.get(key) || '']))
  const page = Number(filters.page) || 1
  const [searchText, setSearchText] = useState(filters.search)

  const query = searchParams.toString()
  const loader = useCallback(() => {
    const params = Object.fromEntries(new URLSearchParams(query))
    return listUsers({ ...params, page_size: PAGE_SIZE })
  }, [query])
  const { data, error, loading } = useApi(loader)

  const update = (changes) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)))
    if (!('page' in changes)) next.delete('page')
    setSearchParams(next)
  }

  const titleFilter = filters.has_staff_profile === 'false' ? 'none' : filters.job_title
  const hasFilters = FILTER_KEYS.some((key) => key !== 'page' && filters[key])

  return (
    <>
      {/* "New staff account" is the top-bar primary action for admins, so it is not repeated here. */}
      <PageHeader eyebrow="Administration" title="Users & access" />

      <Panel flush>
        <form
          className="filter-bar"
          role="search"
          onSubmit={(event) => {
            event.preventDefault()
            update({ search: searchText.trim() })
          }}
        >
          <TextField
            className="filter-bar__search"
            label="Search"
            name="search"
            placeholder="Name, username or email"
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            endAdornment={
              <button type="submit" className="field__icon-button" aria-label="Search">
                <SearchIcon size={18} />
              </button>
            }
          />
          <SelectField
            label="Role"
            placeholder="All roles"
            options={ROLE_OPTIONS}
            value={filters.role}
            onChange={(event) => update({ role: event.target.value })}
          />
          <SelectField
            label="Job title"
            placeholder="All job titles"
            options={TITLE_FILTER_OPTIONS}
            value={titleFilter}
            onChange={(event) => {
              const value = event.target.value
              update(value === 'none' ? { job_title: '', has_staff_profile: 'false' }
                : { job_title: value, has_staff_profile: '' })
            }}
          />
          <SelectField
            label="Status"
            placeholder="Any status"
            options={STATUS_OPTIONS}
            value={filters.is_active}
            onChange={(event) => update({ is_active: event.target.value })}
          />
          {hasFilters && (
            <Button
              variant="link"
              className="filter-bar__clear"
              onClick={() => {
                setSearchText('')
                setSearchParams(new URLSearchParams())
              }}
            >
              Clear filters
            </Button>
          )}
        </form>

        {error && (
          <div className="panel-inset">
            <Alert variant="error">{getErrorMessage(error, 'Could not load users.')}</Alert>
          </div>
        )}

        {loading && !data ? (
          <LoadingBlock label="Loading users" />
        ) : data?.results.length ? (
          <>
            <div className="table-wrap" aria-busy={loading}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Name</th>
                    <th scope="col">Role / job title</th>
                    <th scope="col" className="hide-sm">Department</th>
                    <th scope="col">Status</th>
                    <th scope="col" className="hide-sm">Last sign-in</th>
                    <th scope="col"><span className="visually-hidden">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((account) => (
                    <tr key={account.id}>
                      <td>
                        <div className="cell-primary">{account.full_name || account.username}</div>
                        <div className="cell-secondary">
                          @{account.username}
                          {account.email && ` · ${account.email}`}
                        </div>
                      </td>
                      <td>{accountTitle(account)}</td>
                      <td className="hide-sm">{account.department || '—'}</td>
                      <td>{accountBadge(account)}</td>
                      <td className="hide-sm">{account.last_login ? formatDateTime(account.last_login) : 'Never'}</td>
                      <td className="cell-actions">
                        <Link to={`/admin/users/${account.id}`}>Manage</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} count={data.count}
              onPageChange={(next) => update({ page: String(next) })} />
          </>
        ) : (
          <EmptyState icon={UsersIcon} title={hasFilters ? 'No accounts match these filters' : 'No accounts yet'}>
            {hasFilters ? 'Try a different search or clear the filters.' : 'Create the first staff account.'}
          </EmptyState>
        )}
      </Panel>
    </>
  )
}
