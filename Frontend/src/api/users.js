// User management (super_admin only on the backend).
import { authRequest, toQuery } from './http'

/** params: { search, role, job_title, is_active, has_staff_profile, ordering, page, page_size } */
export function listUsers(params = {}) {
  return authRequest(`/users/${toQuery(params)}`)
}

export function getUser(id) {
  return authRequest(`/users/${id}/`)
}

/** Create a staff account (User + Staff profile). */
export function createStaffAccount(data) {
  return authRequest('/users/', { method: 'POST', body: data })
}

export function updateUser(id, changes) {
  return authRequest(`/users/${id}/`, { method: 'PATCH', body: changes })
}

export function setUserActive(id, active) {
  return authRequest(`/users/${id}/${active ? 'activate' : 'deactivate'}/`, { method: 'POST' })
}

/** Total number of accounts matching a filter (reads `count` from a 1-item page). */
export async function countUsers(params = {}) {
  const data = await listUsers({ ...params, page_size: 1 })
  return data.count
}
