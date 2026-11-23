from django.urls import path

from . import views

# Mounted under /api/ in config/urls.py.
urlpatterns = [
    path('lab/tests/', views.LabTestListView.as_view(), name='lab_test_list'),
    path('lab/orders/', views.LabOrderListCreateView.as_view(), name='lab_order_list'),
    path('lab/orders/<int:pk>/', views.LabOrderDetailView.as_view(), name='lab_order_detail'),
    path('lab/orders/<int:pk>/cancel/', views.LabOrderCancelView.as_view(), name='lab_order_cancel'),
    path('lab/orders/<int:pk>/release/', views.LabOrderReleaseView.as_view(), name='lab_order_release'),
    path('lab/pending/', views.PendingTestsView.as_view(), name='lab_pending'),
    path('lab/results/<int:pk>/enter/', views.ResultEntryView.as_view(), name='lab_result_enter'),
    path('lab/patients/<int:patient_id>/results/', views.PatientResultsView.as_view(), name='lab_patient_results'),
    path('lab/patients/<int:patient_id>/trends/', views.PatientTrendView.as_view(), name='lab_patient_trends'),
    path('lab/my/orders/', views.MyLabOrdersView.as_view(), name='lab_my_orders'),
    path('lab/my/results/', views.MyResultsView.as_view(), name='lab_my_results'),
    path('lab/my/trends/', views.MyTrendView.as_view(), name='lab_my_trends'),
]
