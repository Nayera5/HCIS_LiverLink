import { useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import SelectField from '../../components/ui/SelectField'
import TextAreaField from '../../components/ui/TextAreaField'
import TextField from '../../components/ui/TextField'
import { changedPlanFields, PLAN_TYPE_OPTIONS, todayIso, validatePlan } from './rxFormat'

const blank = () => ({ plan_type: '', goals: '', steps: '', start_date: todayIso(), review_date: '', reason: '' })

/**
 * Create or edit a treatment plan. When `plan` is given the form edits it: only changed fields are
 * sent, and a reason is required (stored in the audit log with the old and new values).
 * onSubmit(payload) must return a promise.
 */
export default function PlanForm({ plan, onSubmit, onCancel, canReferTransplant = false }) {
  const editing = Boolean(plan)
  const planTypeOptions = canReferTransplant || plan?.plan_type === 'transplant_referral'
    ? PLAN_TYPE_OPTIONS
    : PLAN_TYPE_OPTIONS.filter((option) => option.value !== 'transplant_referral')
  const [form, setForm] = useState(() => (editing
    ? { plan_type: plan.plan_type, goals: plan.goals, steps: plan.steps || '', start_date: plan.start_date,
        review_date: plan.review_date || '', reason: '' }
    : blank()))
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const set = (key) => (event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    const found = validatePlan(form, { editing })
    let payload
    if (editing) {
      const changes = changedPlanFields(plan, form)
      if (!Object.keys(changes).length) found.form = 'Nothing has changed.'
      payload = { ...changes, reason: form.reason.trim() }
    } else {
      payload = { plan_type: form.plan_type, goals: form.goals.trim(), steps: form.steps.trim(),
        start_date: form.start_date, review_date: form.review_date || null }
    }
    setErrors(found)
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      await onSubmit(payload)
    } catch (err) {
      const fields = fieldErrors(err)
      setErrors(Object.keys(fields).length ? fields : { form: getErrorMessage(err, 'Could not save the plan.') })
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate className="form-stack rx-plan-form">
      {errors.form && <Alert variant="error">{errors.form}</Alert>}
      <div className="rx-grid">
        <SelectField label="Treatment" placeholder="Choose…" options={planTypeOptions} value={form.plan_type}
          onChange={set('plan_type')} error={errors.plan_type} />
        <TextField label="Start date" type="date" value={form.start_date} onChange={set('start_date')}
          error={errors.start_date} />
        <TextField label="Review date (optional)" type="date" value={form.review_date} min={form.start_date || undefined}
          onChange={set('review_date')} error={errors.review_date} />
      </div>
      <TextAreaField label="Goals" value={form.goals} onChange={set('goals')} error={errors.goals}
        placeholder="e.g. Downstage HCC to within Milan criteria" />
      <TextAreaField label="Steps" optional rows={4} value={form.steps} onChange={set('steps')} error={errors.steps}
        placeholder={'e.g. 1. TACE session\n2. CT after 4 weeks\n3. MDT review'} />
      {editing && (
        <TextAreaField label="Reason for change" value={form.reason} onChange={set('reason')} error={errors.reason}
          hint="Required. Saved in the audit log together with the old and new values." maxLength={2000} />
      )}
      <div className="inline-actions">
        <Button variant="secondary" onClick={onCancel} disabled={saving}>Cancel</Button>
        <Button type="submit" loading={saving}>{editing ? 'Save changes' : 'Create plan'}</Button>
      </div>
    </form>
  )
}
