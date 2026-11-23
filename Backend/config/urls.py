"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Accounts (Person 1): logout, me, passwords, user management.
    path('api/', include('apps.accounts.urls')),
    # Patient & donor registry (Person 1): patients, self-registration, own record.
    path('api/', include('apps.registry.urls')),
    # EMR (module 4): encounters, history, diagnoses, vitals, documents.
    path('api/emr/', include('apps.emr.urls')),
    # Appointment & scheduling (module 3): doctor schedules, free slots, appointments.
    path('api/scheduling/', include('apps.scheduling.urls')),
    path('api/', include('apps.billing.urls')),
    path('api/', include('apps.notifications.urls')),
    # Transplant case management and follow-up (modules 11-12, Person 4).
    path('api/transplant/', include('apps.transplant.urls')),
]
