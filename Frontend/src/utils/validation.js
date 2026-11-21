// Client-side checks only improve feedback; the backend remains the authority.

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Mirrors Django's UnicodeUsernameValidator (letters, digits and @ . + - _) and its 150-char limit.
const USERNAME_PATTERN = /^[\p{L}\p{N}_.@+-]+$/u
const USERNAME_MAX_LENGTH = 150

// Usernames are case-sensitive at login, so the value is never lowercased here.
export function validateUsername(value) {
  const username = value.trim()
  if (!username) return 'Enter your username.'
  if (username.length > USERNAME_MAX_LENGTH) {
    return `Usernames are at most ${USERNAME_MAX_LENGTH} characters.`
  }
  if (!USERNAME_PATTERN.test(username)) {
    return 'Usernames can only contain letters, numbers and @ . + - _ characters.'
  }
  return ''
}

export function validateEmail(value) {
  const email = value.trim()
  if (!email) return 'Enter your email address.'
  if (email.length > 254 || !EMAIL_PATTERN.test(email)) {
    return 'Enter a valid email address, like name@example.com.'
  }
  return ''
}

// Portal sign-up phone: exactly 11 digits (0-9 only), kept as a string so the leading 0 stays.
const SIGNUP_PHONE_PATTERN = /^[0-9]{11}$/
export const SIGNUP_PHONE_LENGTH = 11

export function validateSignupPhone(value) {
  const phone = (value ?? '').trim()
  if (!phone) return 'Enter your phone number.'
  if (!SIGNUP_PHONE_PATTERN.test(phone)) {
    return 'Enter an 11-digit phone number using numbers only, e.g. 01012345678.'
  }
  return ''
}

export function validatePassword(value) {
  if (!value) return 'Enter your password.'
  return ''
}

export function validateLoginForm({ username, password }) {
  const errors = {}
  const usernameError = validateUsername(username)
  const passwordError = validatePassword(password)
  if (usernameError) errors.username = usernameError
  if (passwordError) errors.password = passwordError
  return errors
}
