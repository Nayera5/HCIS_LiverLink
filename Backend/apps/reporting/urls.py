from django.urls import path

from . import views

# Mounted under /api/ in config/urls.py.
urlpatterns = [
    path('reports/patients/', views.PatientReportView.as_view(), name='report_patients'),
    path('reports/financial/', views.FinancialReportView.as_view(), name='report_financial'),
    path('reports/transplant/', views.TransplantReportView.as_view(), name='report_transplant'),
    path('reports/system-usage/', views.SystemUsageReportView.as_view(), name='report_system_usage'),
]
