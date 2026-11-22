// Thin fetch wrapper for the Django REST backend.
// Base URL comes from VITE_API_URL (see Frontend/.env.example).

export const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api').replace(/\/+$/, '')

export class ApiError extends Error {
  /**
   * @param {string} message  Human-readable summary.
   * @param {object} opts
   * @param {number} opts.status  HTTP status (0 = network failure).
   * @param {object|null} opts.data  Parsed JSON body from the server, if any.
   */
  constructor(message, { status = 0, data = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }

  get isNetworkError() {
    return this.status === 0
  }
}

export async function apiRequest(path, { method = 'GET', body, headers = {}, signal } = {}) {
  let response
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined && { 'Content-Type': 'application/json' }),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw new ApiError('Network request failed', { status: 0 })
  }

  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = null
    }
  }

  if (!response.ok) {
    throw new ApiError(data?.detail || `Request failed with status ${response.status}`, {
      status: response.status,
      data,
    })
  }
  return data
}
