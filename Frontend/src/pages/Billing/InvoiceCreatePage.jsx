import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { createInvoice, listServices } from '../../api/billing'
import { fieldErrors } from '../../api/http'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { LoadingBlock } from '../../components/ui/Feedback'
import { PlusIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { useApi } from '../../hooks/useApi'
import { formatMoney } from './billingDisplay'
import PatientPicker from './PatientPicker'
import './Billing.css'

function todayISO() {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

const EMPTY_ITEM = { service: '', quantity: '1' }

export default function InvoiceCreatePage() {
  const navigate = useNavigate()
  const loadServices = useCallback(() => listServices({ active_only: 'true', page_size: 100 }), [])
  const { data: serviceData, loading: loadingServices } = useApi(loadServices)

  const [patient, setPatient] = useState(null)
  const [dueDate, setDueDate] = useState('')
  const [items, setItems] = useState([{ ...EMPTY_ITEM }])
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const services = serviceData?.results || []
  const serviceOptions = services.map((s) => ({
    value: String(s.id),
    label: `${s.name}${s.standard_code ? ` [${s.standard_code}]` : ''} (${formatMoney(s.price)})`,
  }))

  const updateItem = (index, changes) => {
    setItems((prev) => prev.map((item, i) => (i === index ? { ...item, ...changes } : item)))
  }
  const addItem = () => setItems((prev) => [...prev, { ...EMPTY_ITEM }])
  const removeItem = (index) => setItems((prev) => prev.filter((_, i) => i !== index))

  const estimatedTotal = items.reduce((sum, item) => {
    const service = services.find((s) => String(s.id) === item.service)
    const quantity = Number(item.quantity) || 0
    return sum + (service ? Number(service.price) * quantity : 0)
  }, 0)

  const validate = () => {
    const found = {}
    if (!patient) found.patient = 'Find and select a patient.'
    if (!dueDate) found.due_date = 'Choose a due date.'
    else if (dueDate < todayISO()) found.due_date = 'The due date cannot be in the past.'
    items.forEach((item, index) => {
      if (!item.service) found[`item_${index}`] = 'Choose a service.'
      else if (!(Number(item.quantity) >= 1)) found[`item_${index}`] = 'Quantity must be at least 1.'
    })
    return found
  }

  const submit = async (event) => {
    event.preventDefault()
    const found = validate()
    setErrors(found)
    setFormError('')
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      const invoice = await createInvoice({
        patient: patient.id,
        due_date: dueDate,
        items: items.map((item) => ({ service: Number(item.service), quantity: Number(item.quantity) })),
      })
      navigate(`/billing/invoices/${invoice.id}`, { state: { flash: 'Invoice created.' } })
    } catch (error) {
      const { form, ...rest } = fieldErrors(error)
      setErrors(rest)
      setFormError(form || (Object.keys(rest).length ? 'Please correct the highlighted fields.'
        : getErrorMessage(error, 'Could not create the invoice.')))
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader back={{ to: '/billing/invoices', label: 'Invoices' }} eyebrow="Billing & payments"
        title="New invoice" />
      <Panel title="Invoice details">
        <form onSubmit={submit} noValidate className="form-stack">
          {formError && <Alert variant="error">{formError}</Alert>}

          <PatientPicker value={patient} onChange={setPatient} error={errors.patient} />

          <TextField label="Due date" name="due_date" type="date" min={todayISO()} value={dueDate}
            onChange={(event) => setDueDate(event.target.value)} error={errors.due_date} />

          <div className="field">
            <div className="field__label-row">
              <label className="field__label">Services</label>
            </div>
            {loadingServices ? (
              <LoadingBlock label="Loading services" />
            ) : (
              <div className="table-wrap invoice-items-table">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th scope="col">Service</th>
                      <th scope="col">Quantity</th>
                      <th scope="col"><span className="visually-hidden">Remove</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item, index) => (
                      <tr key={index}>
                        <td>
                          <SelectField label="Service" value={item.service} placeholder="Choose a service"
                            options={serviceOptions} error={errors[`item_${index}`]}
                            className="field--compact"
                            onChange={(event) => updateItem(index, { service: event.target.value })} />
                        </td>
                        <td>
                          <TextField label="Quantity" type="number" min="1" value={item.quantity}
                            className="field--compact"
                            onChange={(event) => updateItem(index, { quantity: event.target.value })} />
                        </td>
                        <td className="cell-actions">
                          {items.length > 1 && (
                            <Button variant="link" size="sm" onClick={() => removeItem(index)}>Remove</Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <Button type="button" variant="secondary" size="sm" icon={PlusIcon} onClick={addItem}
              className="section-gap">
              Add another service
            </Button>
          </div>

          <div className="invoice-summary">
            <div className="invoice-summary__item">
              <span className="invoice-summary__label">Estimated total</span>
              <span className="invoice-summary__value">{formatMoney(estimatedTotal)}</span>
            </div>
          </div>

          <div className="form-actions">
            <Button variant="secondary" onClick={() => navigate('/billing/invoices')} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" loading={saving}>Create invoice</Button>
          </div>
        </form>
      </Panel>
    </>
  )
}
