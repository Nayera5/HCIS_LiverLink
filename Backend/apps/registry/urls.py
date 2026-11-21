from django.urls import path

from . import views

# Mounted under /api/ in config/urls.py.
urlpatterns = [
    path('patients/', views.PatientListCreateView.as_view(), name='patient_list'),
    path('patients/register/', views.SelfRegistrationView.as_view(), name='patient_self_register'),
    path('patients/me/', views.MyPatientRecordView.as_view(), name='patient_me'),
    path('patients/summary/', views.PatientSummaryView.as_view(), name='patient_summary'),
    path('patients/<int:pk>/', views.PatientDetailView.as_view(), name='patient_detail'),
    path('patients/<int:pk>/category/', views.PatientCategoryView.as_view(), name='patient_category'),
]
