import { useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { getMyNotifications, markAllNotificationsRead, markNotificationRead } from '../../api/notifications'
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

export default function NotificationsPage() {
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
    } catch (err) {
      setActionError(getErrorMessage(err, 'Could not mark this notification as read.'))
    } finally {
      setMarkingId(null)
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
                <div className="notification-item__main">
                  <div className="notification-item__header">
                    {typeBadge(notification.type)}
                    <span className="notification-item__time">{formatDateTime(notification.sent_at)}</span>
                  </div>
                  {notification.title && <p className="notification-item__title">{notification.title}</p>}
                  <p className="notification-item__message">{notification.message}</p>
                </div>
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
