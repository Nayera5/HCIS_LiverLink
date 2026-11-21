// Run with `npm test` (Node's built-in test runner; no extra dependencies).
import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import { validatePassword, validateSignupPhone } from './validation.js'

describe('validateSignupPhone', () => {
  test('accepts exactly 11 digits, including a leading zero', () => {
    assert.equal(validateSignupPhone('01012345678'), '')
    assert.equal(validateSignupPhone('  01012345678  '), '') // surrounding spaces are trimmed
  })

  test('requires a phone number', () => {
    for (const value of ['', '   ', undefined, null]) {
      assert.equal(validateSignupPhone(value), 'Enter your phone number.')
    }
  })

  test('rejects anything other than 11 digits', () => {
    const invalid = [
      '0101234567', // 10 digits
      '010123456789', // 12 digits
      '0101234567a',
      '+2010123456',
      '010-1234-567',
      '0101 234567',
      '٠١٠١٢٣٤٥٦٧٨', // Arabic-Indic digits
    ]
    for (const value of invalid) {
      assert.match(validateSignupPhone(value), /11-digit/, value)
    }
  })
})

describe('validatePassword', () => {
  test('does not reject a password that contains the username', () => {
    // Similarity to the username is no longer checked for sign-up (the backend enforces the rest).
    assert.equal(validatePassword('Mona.Ali2026'), '')
  })
})
