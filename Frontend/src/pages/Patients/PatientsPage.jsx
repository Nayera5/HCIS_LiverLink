import { useCallback, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { listPatients } from '../../api/patients'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock, Pagination } from '../../components/ui/Feedback'
import { ClipboardIcon, PlusIcon, SearchIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { formatDate } from '../../utils/format'
import { ageSex, CATEGORY_OPTIONS, categoryBadge, patientName, SEX_OPTIONS } from './patientDisplay'
import '../Users/Users.css'
import './Patients.css'

const PAGE_SIZE = 20
const FILTER_KEYS = ['search', 'category', 'sex', 'page']

export default function PatientsPage() {
  const { can } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = Object.fromEntries(FILTER_KEYS.map((key) => [key, searchParams.get(key) || '']))
  const page = Number(filters.page) || 1
  const [searchText, setSearchText] = useState(filters.search)
  const [lastUrlSearch, setLastUrlSearch] = useState(filters.search)
  if (filters.search !== lastUrlSearch) {
    // The top-bar search changed the URL: keep the box in sync.
    setLastUrlSearch(filters.search)
    setSearchText(filters.search)
  }

  const query = searchParams.toString()
  const loader = useCallback(
    () => listPatients({ ...Object.fromEntries(new URLSearchParams(query)), page_size: PAGE_SIZE }),
    [query],
  )
  const { data, error, loading } = useApi(loader)

  const update = (changes) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)))
    if (!('page' in changes)) next.delete('page')
    setSearchParams(next)
  }
  const hasFilters = FILTER_KEYS.some((key) => key !== 'page' && filters[key])
  // Coordinators get "Register patient" in the top bar; super admins' top-bar action is staff accounts.
  const showRegister = can('patients.register') && can('users.manage')

  return (
    <>
      <PageHeader
        eyebrow="Patient & donor registry"
        title="Patients"
        actions={showRegister && (
          <Button as={Link} to="/patients/new" icon={PlusIcon}>Register patient</Button>
        )}
      />

      <Panel flush>
        <form className="filter-bar filter-bar--patients" role="search"
          onSubmit={(event) => {
            event.preventDefault()
            update({ search: searchText.trim() })
          }}>
          <TextField className="filter-bar__search" label="Search" name="search"
            placeholder="Name, MRN, national ID or phone" value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            endAdornment={
              <button type="submit" className="field__icon-button" aria-label="Search patients">
                <SearchIcon size={18} />
              </button>
            } />
          <SelectField label="Category" placeholder="All categories" options={CATEGORY_OPTIONS}
            value={filters.category} onChange={(event) => update({ category: event.target.value })} />
          <SelectField label="Sex" placeholder="Any" options={SEX_OPTIONS} value={filters.sex}
            onChange={(event) => update({ sex: event.target.value })} />
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
            <Alert variant="error">{getErrorMessage(error, 'Could not load patients.')}</Alert>
          </div>
        )}

        {loading && !data ? (
          <LoadingBlock label="Loading patients" />
        ) : data?.results.length ? (
          <>
            <div className="table-wrap" aria-busy={loading}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Patient</th>
                    <th scope="col">Category</th>
                    <th scope="col" className="hide-sm">Phone</th>
                    <th scope="col" className="hide-sm">Registered</th>
                    <th scope="col"><span className="visually-hidden">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((patient) => (
                    <tr key={patient.id}>
                      <td>
                        <div className="cell-primary">{patientName(patient)}</div>
                        <div className="cell-secondary">{patient.mrn} · {ageSex(patient)}</div>
                      </td>
                      <td>{categoryBadge(patient.category)}</td>
                      <td className="hide-sm">{patient.phone}</td>
                      <td className="hide-sm">{formatDate(patient.created_at)}</td>
                      <td className="cell-actions">
                        <Link to={`/patients/${patient.id}`}>Open patient</Link>
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
          <EmptyState icon={ClipboardIcon} title={hasFilters ? 'No patients match' : 'No patients registered yet'}>
            {hasFilters ? 'Try another name, MRN or national ID, or clear the filters.'
              : can('patients.register') ? 'Register the first patient to create a record with an MRN.'
                : 'Patients appear here once they are registered.'}
          </EmptyState>
        )}
      </Panel>
    </>
  )
}
