from django.urls import path

from . import views

# Mounted under /api/ in config/urls.py.
urlpatterns = [
    path('notifications/me/', views.MyNotificationsView.as_view(), name='notification_mine'),
    path('notifications/read-all/', views.MarkAllNotificationsReadView.as_view(), name='notification_read_all'),
    path('notifications/<int:pk>/read/', views.MarkNotificationReadView.as_view(), name='notification_read'),
]
