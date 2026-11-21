import { useCallback, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { listApplications } from '../../api/donorApplications'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock, Pagination } from '../../components/ui/Feedback'
import { PlusIcon, SearchIcon, UserPlusIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { formatDate } from '../../utils/format'
import { statusBadge } from './applicationDisplay'
import { STATUS_FILTER_OPTIONS } from './donorApplicationRules'
import '../Users/Users.css'
import './DonorApplications.css'

const PAGE_SIZE = 20
const FILTER_KEYS = ['status', 'search', 'page']

/** Staff list (donor_applications.view). Newest first; filters live in the URL. */
export default function DonorApplicationsPage() {
  const { can } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = Object.fromEntries(FILTER_KEYS.map((key) => [key, searchParams.get(key) || '']))
  const page = Number(filters.page) || 1
  const [searchText, setSearchText] = useState(filters.search)

  const query = searchParams.toString()
  const loader = useCallback(() => {
    const params = Object.fromEntries(new URLSearchParams(query))
    return listApplications({ ...params, page_size: PAGE_SIZE })
  }, [query])
  const { data, error, loading } = useApi(loader)

  const update = (changes) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)))
    if (!('page' in changes)) next.delete('page')
    setSearchParams(next)
  }
  const hasFilters = Boolean(filters.status || filters.search)

  return (
    <>
      <PageHeader
        eyebrow="Patient & donor registry"
        title="Donor applications"
        actions={can('donor_applications.submit_on_behalf') && (
          <Button as={Link} to="/donor-applications/new" icon={PlusIcon}>New application</Button>
        )}
      />

      <Panel flush>
        <form className="filter-bar filter-bar--applications" role="search"
          onSubmit={(event) => {
            event.preventDefault()
            update({ search: searchText.trim() })
          }}>
          <TextField className="filter-bar__search" label="Search" name="search"
            placeholder="Donor or recipient name or MRN" value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            endAdornment={
              <button type="submit" className="field__icon-button" aria-label="Search applications">
                <SearchIcon size={18} />
              </button>
            } />
          <SelectField label="Status" placeholder="Any status" options={STATUS_FILTER_OPTIONS}
            value={filters.status} onChange={(event) => update({ status: event.target.value })} />
          {hasFilters && (
            <Button variant="link" className="filter-bar__clear" onClick={() => {
              setSearchText('')
              setSearchParams(new URLSearchParams())
            }}>
              Clear filters
            </Button>
          )}
        </form>

        {error && (
          <div className="panel-inset">
            <Alert variant="error">{getErrorMessage(error, 'Could not load donor applications.')}</Alert>
          </div>
        )}

        {loading && !data ? (
          <LoadingBlock label="Loading donor applications" />
        ) : data?.results.length ? (
          <>
            <div className="table-wrap" aria-busy={loading}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Donor</th>
                    <th scope="col">Recipient</th>
                    <th scope="col" className="hide-sm">Relationship</th>
                    <th scope="col">Status</th>
                    <th scope="col" className="hide-sm">Submitted</th>
                    <th scope="col"><span className="visually-hidden">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((app) => (
                    <tr key={app.id}>
                      <td>
                        <div className="cell-primary">{app.donor.name}</div>
                        <div className="cell-secondary">{app.donor.mrn}</div>
                      </td>
                      <td>
                        <div className="cell-primary">{app.recipient.name}</div>
                        <div className="cell-secondary">{app.recipient.mrn}</div>
                      </td>
                      <td className="hide-sm">{app.relationship}</td>
                      <td>{statusBadge(app.status)}</td>
                      <td className="hide-sm">{formatDate(app.submitted_at)}</td>
                      <td className="cell-actions">
                        <Link to={`/donor-applications/${app.id}`}>
                          {can('donor_applications.screen') && app.next_statuses.length ? 'Review' : 'Open'}
                        </Link>
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
          <EmptyState icon={UserPlusIcon} title={hasFilters ? 'No applications match these filters' : 'No donor applications yet'}>
            {hasFilters ? 'Try a different search or clear the filters.' : 'Applications submitted by donors appear here.'}
          </EmptyState>
        )}
      </Panel>
    </>
  )
}
