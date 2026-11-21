// Run with `npm test` (Node's built-in test runner; no extra dependencies).
import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import { validateStaffForm } from './userFormFields.js'

const VALID_NEW_STAFF = {
  username: 'dr.mona', password: 'Very-Strong-Pass!1', confirmPassword: 'Very-Strong-Pass!1',
  first_name: 'Mona', last_name: 'Elsayed', email: '', job_title: 'hepatologist',
  department: '', license_no: '', phone: '',
}

describe('validateStaffForm (creating a staff account)', () => {
  test('a complete form has no errors', () => {
    assert.deepEqual(validateStaffForm(VALID_NEW_STAFF, { creating: true }), {})
  })

  test('job title is required', () => {
    const errors = validateStaffForm({ ...VALID_NEW_STAFF, job_title: '' }, { creating: true })
    assert.deepEqual(errors, { job_title: 'Choose a job title.' })
  })
})
