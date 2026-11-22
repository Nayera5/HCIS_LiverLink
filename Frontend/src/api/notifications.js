// Notifications API (backend: apps.notifications). Always the signed-in user's own notifications.
import { authRequest, toQuery } from './http'

/** { unread_count, notifications: [...] }. params: { unread: 'true' } to show unread only. */
export function getMyNotifications(params = {}) {
  return authRequest(`/notifications/me/${toQuery(params)}`)
}

export function markNotificationRead(id) {
  return authRequest(`/notifications/${id}/read/`, { method: 'POST' })
}

export function markAllNotificationsRead() {
  return authRequest('/notifications/read-all/', { method: 'POST' })
}
