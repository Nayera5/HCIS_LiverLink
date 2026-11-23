import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { createService, listServices, updateService } from '../../api/billing'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock, Pagination } from '../../components/ui/Feedback'
import { PlusIcon, ReceiptIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import {
  CODING_SYSTEM_LABELS,
  CODING_SYSTEM_OPTIONS,
  formatMoney,
  SERVICE_CATEGORY_LABELS,
  SERVICE_CATEGORY_OPTIONS,
  SERVICE_STATUS_OPTIONS,
} from './billingDisplay'
import '../Users/Users.css'
import '../Patients/Patients.css'
import './Billing.css'

const PAGE_SIZE = 10
const FILTER_KEYS = ['status', 'coding_system', 'category']

const EMPTY_FORM = {
  code: '',
  name: '',
  category: '',
  coding_system: '',
  standard_code: '',
  price: '',
}

function validate(values) {
  const errors = {}
  if (!values.code.trim()) errors.code = 'Enter a service code.'
  if (!values.name.trim()) errors.name = 'Enter a display name.'
  if (!values.category) errors.category = 'Choose a category.'
  if (values.price === '' || Number(values.price) < 0) errors.price = 'Enter a price of 0 or more.'
  return errors
}

function NewServiceForm({ onCreated }) {
  const [values, setValues] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const change = (event) => setValues((prev) => ({ ...prev, [event.target.name]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    const found = validate(values)
    setErrors(found)
    setFormError('')
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      const created = await createService({ ...values, code: values.code.trim(), name: values.name.trim() })
      onCreated(created)
      setValues(EMPTY_FORM)
    } catch (error) {
      const { form, ...rest } = fieldErrors(error)
      setErrors(rest)
      setFormError(form || (Object.keys(rest).length ? '' : getErrorMessage(error, 'Could not add the service.')))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Panel title="Add a service">
      <form onSubmit={submit} noValidate className="form-stack">
        {formError && <Alert variant="error">{formError}</Alert>}
        <div className="form-grid__pair">
          <TextField label="Code" name="code" maxLength={30} value={values.code} onChange={change}
            error={errors.code} placeholder="CONS-01" />
          <TextField label="Name" name="name" maxLength={150} value={values.name} onChange={change}
            error={errors.name} placeholder="Consultation" />
        </div>
        <div className="form-grid__pair">
          <SelectField label="Category" name="category" value={values.category} onChange={change}
            error={errors.category} placeholder="Choose a category" options={SERVICE_CATEGORY_OPTIONS} />
          <TextField label="Price (EGP)" name="price" type="number" min="0" step="0.01" value={values.price}
            onChange={change} error={errors.price} />
        </div>
        <div className="form-grid__pair">
          <SelectField label="Coding System" name="coding_system" value={values.coding_system} onChange={change}
            placeholder="None" options={CODING_SYSTEM_OPTIONS} />
          <TextField label="Standard Code" name="standard_code" maxLength={50} value={values.standard_code}
            onChange={change} placeholder="e.g. 99213" />
        </div>
        <div className="form-actions">
          <Button type="submit" icon={PlusIcon} loading={saving}>Add service</Button>
        </div>
      </form>
    </Panel>
  )
}

function EditServiceRow({ service, onCancel, onSaved }) {
  const [values, setValues] = useState({
    name: service.name,
    category: service.category,
    coding_system: service.coding_system || '',
    standard_code: service.standard_code || '',
    price: service.price,
  })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  const change = (event) => setValues((prev) => ({ ...prev, [event.target.name]: event.target.value }))

  const save = async () => {
    const found = validate({ ...values, code: service.code })
    setErrors(found)
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      const updated = await updateService(service.id, values)
      onSaved(updated)
    } catch (error) {
      setErrors(fieldErrors(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <tr>
      <td><div className="cell-primary">{service.code}</div></td>
      <td><TextField label="Name" name="name" value={values.name} onChange={change} error={errors.name}
        className="field--compact" /></td>
      <td><SelectField label="Category" name="category" value={values.category} onChange={change}
        options={SERVICE_CATEGORY_OPTIONS} className="field--compact" /></td>
      <td><SelectField label="Coding System" name="coding_system" value={values.coding_system} onChange={change}
        placeholder="None" options={CODING_SYSTEM_OPTIONS} className="field--compact" /></td>
      <td><TextField label="Standard Code" name="standard_code" maxLength={50} value={values.standard_code}
        onChange={change} className="field--compact" /></td>
      <td><TextField label="Price" name="price" type="number" min="0" step="0.01" value={values.price}
        onChange={change} error={errors.price} className="field--compact" /></td>
      <td className="hide-sm">—</td>
      <td className="cell-actions">
        <Button size="sm" loading={saving} onClick={save}>Save</Button>{' '}
        <Button size="sm" variant="secondary" onClick={onCancel} disabled={saving}>Cancel</Button>
      </td>
    </tr>
  )
}

export default function ServiceCatalogPage() {
  const { can } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = Object.fromEntries(FILTER_KEYS.map((key) => [key, searchParams.get(key) || '']))
  const page = Number(searchParams.get('page')) || 1
  const query = searchParams.toString()
  const loader = useCallback(
    () => listServices({ ...Object.fromEntries(new URLSearchParams(query)), page_size: PAGE_SIZE }),
    [query],
  )
  const { data, error, loading, reload, setData } = useApi(loader)
  const [editingId, setEditingId] = useState(null)
  const canManage = can('billing.manage_services')

  // Changing a filter starts again from page 1; only an explicit page change keeps `page`.
  const updateFilter = (changes) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)))
    if (!('page' in changes)) next.delete('page')
    setSearchParams(next)
  }
  const hasFilters = FILTER_KEYS.some((key) => filters[key])

  // A stale or hand-edited ?page= past the last page gets a 404 from the API: fall back to page 1.
  const pageOutOfRange = error?.status === 404 && page > 1
  useEffect(() => {
    if (!pageOutOfRange) return
    const next = new URLSearchParams(searchParams)
    next.delete('page')
    setSearchParams(next, { replace: true })
  }, [pageOutOfRange, searchParams, setSearchParams])

  const goToPage = (next) => {
    setEditingId(null)
    updateFilter({ page: next > 1 ? String(next) : '' })
  }

  const replace = (service) => {
    setData((prev) => ({ ...prev, results: prev.results.map((s) => (s.id === service.id ? service : s)) }))
    setEditingId(null)
  }
  // The new service lands wherever its name sorts, so refetch the current page (and the count).
  const created = () => reload()
  const toggleActive = async (service) => {
    const updated = await updateService(service.id, { is_active: !service.is_active })
    replace(updated)
  }

  return (
    <>
      <PageHeader eyebrow="Billing & payments" title="Service catalog" />

      <div className="content-stack">
        {canManage && <NewServiceForm onCreated={created} />}

        <Panel flush title="Services">
          <form className="filter-bar" onSubmit={(event) => event.preventDefault()}>
            <SelectField label="Status" placeholder="Any status" options={SERVICE_STATUS_OPTIONS}
              value={filters.status} onChange={(event) => updateFilter({ status: event.target.value })} />
            <SelectField label="Coding System" placeholder="Any coding system" options={CODING_SYSTEM_OPTIONS}
              value={filters.coding_system}
              onChange={(event) => updateFilter({ coding_system: event.target.value })} />
            <SelectField label="Category" placeholder="Any category" options={SERVICE_CATEGORY_OPTIONS}
              value={filters.category}
              onChange={(event) => updateFilter({ category: event.target.value })} />
            {hasFilters && (
              <Button variant="link" className="filter-bar__clear"
                onClick={() => setSearchParams(new URLSearchParams())}>
                Clear filters
              </Button>
            )}
          </form>
          {error && !pageOutOfRange && (
            <div className="panel-inset">
              <Alert variant="error">{getErrorMessage(error, 'Could not load the service catalog.')}</Alert>
            </div>
          )}
          {loading && !data ? (
            <LoadingBlock label="Loading services" />
          ) : data?.results.length ? (
            <>
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th scope="col">Code</th>
                      <th scope="col">Name</th>
                      <th scope="col">Category</th>
                      <th scope="col">Coding System</th>
                      <th scope="col">Standard Code</th>
                      <th scope="col">Price</th>
                      <th scope="col" className="hide-sm">Status</th>
                      <th scope="col"><span className="visually-hidden">Actions</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.results.map((service) => editingId === service.id ? (
                      <EditServiceRow key={service.id} service={service} onCancel={() => setEditingId(null)}
                        onSaved={replace} />
                    ) : (
                      <tr key={service.id}>
                        <td><div className="cell-primary">{service.code}</div></td>
                        <td>{service.name}</td>
                        <td>{SERVICE_CATEGORY_LABELS[service.category] || service.category}</td>
                        <td>{CODING_SYSTEM_LABELS[service.coding_system] || '—'}</td>
                        <td>{service.standard_code || '—'}</td>
                        <td>{formatMoney(service.price)}</td>
                        <td className="hide-sm">
                          {service.is_active ? <Badge tone="success">Active</Badge> : <Badge>Inactive</Badge>}
                        </td>
                        <td className="cell-actions">
                          {canManage && (
                            <>
                              <Button size="sm" variant="link" onClick={() => setEditingId(service.id)}>Edit</Button>{' '}
                              <Button size="sm" variant="link" onClick={() => toggleActive(service)}>
                                {service.is_active ? 'Deactivate' : 'Activate'}
                              </Button>
                            </>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination page={page} pageSize={PAGE_SIZE} count={data.count} onPageChange={goToPage} />
            </>
          ) : (
            <EmptyState icon={ReceiptIcon} title={hasFilters ? 'No services match' : 'No services yet'}>
              {hasFilters
                ? 'Try different filters or clear the current selections.'
                : canManage
                  ? 'Add the first billable service above.'
                  : 'Services appear here once added.'}
            </EmptyState>
          )}
        </Panel>
      </div>
    </>
  )
}
