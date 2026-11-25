import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { getMyNotifications, markAllNotificationsRead, markNotificationRead } from '../../api/notifications'
import { useAuth } from '../../auth/authContext'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { BellIcon } from '../../components/ui/icons'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import { useApi } from '../../hooks/useApi'
import { formatDateTime } from '../../utils/format'
import { typeBadge } from './notificationDisplay'
import './Notifications.css'

function notificationDestination(notification, can) {
  const id = notification.related_id

  if (notification.type === 'appointment_reminder') {
    return can('self.appointments') ? '/my-appointments' : can('appointments.view') ? '/appointments' : '/'
  }
  if (notification.type === 'follow_up_reminder') {
    return can('self.appointments') ? '/my-appointments' : can('transplant.view_followup') ? '/followup' : '/'
  }
  if (notification.type === 'result_ready') {
    if (can('labs.view')) return id ? `/lab/orders/${id}` : '/lab/orders'
    return can('self.lab_results') ? '/my-results' : '/'
  }
  if (notification.type === 'case_update' || notification.type === 'pending_task') {
    if (can('transplant.view')) return id ? `/transplant/cases/${id}` : '/transplant'
    return can('self.medical_records') ? '/my-medical-record' : '/'
  }
  return '/'
}

export default function NotificationsPage() {
  const { can } = useAuth()
  const navigate = useNavigate()
  const { data, error, loading, setData, reload } = useApi(getMyNotifications)
  const [markingAll, setMarkingAll] = useState(false)
  const [markingId, setMarkingId] = useState(null)
  const [actionError, setActionError] = useState('')

  const markOne = async (id) => {
    setMarkingId(id)
    setActionError('')
    try {
      await markNotificationRead(id)
      setData((prev) => ({
        unread_count: Math.max(0, prev.unread_count - 1),
        notifications: prev.notifications.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
      }))
      return true
    } catch (err) {
      setActionError(getErrorMessage(err, 'Could not mark this notification as read.'))
      return false
    } finally {
      setMarkingId(null)
    }
  }

  const openNotification = async (event, notification) => {
    if (notification.is_read) return
    event.preventDefault()
    if (markingId === notification.id) return
    if (await markOne(notification.id)) {
      navigate(notificationDestination(notification, can))
    }
  }

  const markAll = async () => {
    setMarkingAll(true)
    setActionError('')
    try {
      await markAllNotificationsRead()
      reload()
    } catch (err) {
      setActionError(getErrorMessage(err, 'Could not mark all notifications as read.'))
    } finally {
      setMarkingAll(false)
    }
  }

  return (
    <>
      <PageHeader eyebrow="Notifications" title="Notifications"
        actions={data?.unread_count > 0 && (
          <Button variant="secondary" loading={markingAll} onClick={markAll}>Mark all as read</Button>
        )} />

      <Panel flush>
        {error && (
          <div className="panel-inset">
            <Alert variant="error">{getErrorMessage(error, 'Could not load your notifications.')}</Alert>
          </div>
        )}
        {actionError && (
          <div className="panel-inset">
            <Alert variant="error">{actionError}</Alert>
          </div>
        )}

        {loading && !data ? (
          <LoadingBlock label="Loading notifications" />
        ) : data?.notifications.length ? (
          <ul className="notification-list">
            {data.notifications.map((notification) => (
              <li key={notification.id} className={`notification-item ${notification.is_read ? '' : 'notification-item--unread'}`}>
                <Link to={notificationDestination(notification, can)} className="notification-item__main notification-item__link"
                  onClick={(event) => openNotification(event, notification)}>
                  <div className="notification-item__header">
                    {typeBadge(notification.type)}
                    <span className="notification-item__time">{formatDateTime(notification.sent_at)}</span>
                  </div>
                  {notification.title && <p className="notification-item__title">{notification.title}</p>}
                  <p className="notification-item__message">{notification.message}</p>
                </Link>
                {!notification.is_read && (
                  <Button variant="link" size="sm" loading={markingId === notification.id}
                    onClick={() => markOne(notification.id)}>
                    Mark as read
                  </Button>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState icon={BellIcon} title="No notifications yet">
            Reminders, result alerts and case updates will appear here.
          </EmptyState>
        )}
      </Panel>
    </>
  )
}
