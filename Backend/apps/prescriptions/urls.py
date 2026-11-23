from django.urls import path

from . import views

# Mounted under /api/ in config/urls.py.
urlpatterns = [
    path('rx/drugs/', views.DrugListCreateView.as_view(), name='rx_drug_list'),
    path('rx/drugs/<int:pk>/', views.DrugDetailView.as_view(), name='rx_drug_detail'),
    path('rx/prescriptions/', views.PrescriptionListCreateView.as_view(), name='rx_list'),
    path('rx/prescriptions/<int:pk>/', views.PrescriptionDetailView.as_view(), name='rx_detail'),
    path('rx/prescriptions/<int:pk>/stop/', views.PrescriptionStopView.as_view(), name='rx_stop'),
    path('rx/prescriptions/<int:pk>/complete/', views.PrescriptionCompleteView.as_view(), name='rx_complete'),
    path('rx/patients/<int:patient_id>/medications/', views.PatientMedicationsView.as_view(),
         name='rx_patient_medications'),
    path('rx/plans/', views.TreatmentPlanListCreateView.as_view(), name='rx_plan_list'),
    path('rx/plans/<int:pk>/', views.TreatmentPlanDetailView.as_view(), name='rx_plan_detail'),
    path('rx/plans/<int:pk>/complete/', views.TreatmentPlanCompleteView.as_view(), name='rx_plan_complete'),
    path('rx/plans/<int:pk>/cancel/', views.TreatmentPlanCancelView.as_view(), name='rx_plan_cancel'),
    path('rx/my/medications/', views.MyMedicationsView.as_view(), name='rx_my_medications'),
    path('rx/my/plans/', views.MyTreatmentPlansView.as_view(), name='rx_my_plans'),
]
