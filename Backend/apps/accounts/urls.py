from django.urls import path

from . import views

# Mounted under /api/ in config/urls.py. The token endpoints stay where they were:
#   POST /api/auth/token/          (login: username + password)
#   POST /api/auth/token/refresh/
urlpatterns = [
    path('auth/logout/', views.LogoutView.as_view(), name='auth_logout'),
    path('auth/me/', views.MeView.as_view(), name='auth_me'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='auth_change_password'),
    path('auth/password-reset/', views.PasswordResetRequestView.as_view(), name='auth_password_reset'),
    path('auth/password-reset/confirm/', views.PasswordResetConfirmView.as_view(),
         name='auth_password_reset_confirm'),

    path('users/', views.UserListCreateView.as_view(), name='user_list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/activate/', views.UserActivateView.as_view(), name='user_activate'),
    path('users/<int:pk>/deactivate/', views.UserDeactivateView.as_view(), name='user_deactivate'),

    path('audit-logs/', views.AuditLogListView.as_view(), name='audit_log_list'),
]
