from django.urls import path

from . import consent_views, donor_views, views

# Mounted under /api/ in config/urls.py.
urlpatterns = [
    path('patients/', views.PatientListCreateView.as_view(), name='patient_list'),
    path('patients/register/', views.SelfRegistrationView.as_view(), name='patient_self_register'),
    path('patients/me/', views.MyPatientRecordView.as_view(), name='patient_me'),
    path('patients/me/summary/', views.MyPatientSummaryView.as_view(), name='patient_me_summary'),
    path('patients/summary/', views.PatientSummaryView.as_view(), name='patient_summary'),
    path('patients/<int:pk>/', views.PatientDetailView.as_view(), name='patient_detail'),
    path('patients/<int:pk>/category/', views.PatientCategoryView.as_view(), name='patient_category'),

    # Donor applications (Stage 5): donor portal ("mine") and staff screening.
    path('donor-applications/', donor_views.ApplicationListCreateView.as_view(), name='donor_app_list'),
    path('donor-applications/mine/', donor_views.MyApplicationsView.as_view(), name='donor_app_mine'),
    path('donor-applications/mine/<int:pk>/withdraw/', donor_views.MyApplicationWithdrawView.as_view(),
         name='donor_app_mine_withdraw'),
    path('donor-applications/<int:pk>/', donor_views.ApplicationDetailView.as_view(), name='donor_app_detail'),
    path('donor-applications/<int:pk>/status/', donor_views.ApplicationStatusView.as_view(),
         name='donor_app_status'),
    path('donor-applications/<int:pk>/withdraw/', donor_views.ApplicationWithdrawView.as_view(),
         name='donor_app_withdraw'),

    # Consents (Stage 6): surgery consents; staff per patient, portal read-only.
    path('patients/<int:pk>/consents/', consent_views.PatientConsentsView.as_view(), name='patient_consents'),
    path('consents/mine/', consent_views.MyConsentsView.as_view(), name='consent_mine'),
    path('consents/witnesses/', consent_views.ConsentWitnessesView.as_view(), name='consent_witnesses'),
    path('consents/<int:pk>/withdraw/', consent_views.ConsentWithdrawView.as_view(), name='consent_withdraw'),
]
