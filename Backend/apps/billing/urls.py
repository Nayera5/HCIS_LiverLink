from django.urls import path

from . import views

# Mounted under /api/ in config/urls.py.
urlpatterns = [
    path('services/', views.ServiceListCreateView.as_view(), name='service_list'),
    path('services/<int:pk>/', views.ServiceDetailView.as_view(), name='service_detail'),

    path('invoices/', views.InvoiceListCreateView.as_view(), name='invoice_list'),
    path('invoices/me/', views.MyInvoicesView.as_view(), name='invoice_mine'),
    path('invoices/me/<int:pk>/', views.MyInvoiceDetailView.as_view(), name='invoice_mine_detail'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<int:pk>/cancel/', views.InvoiceCancelView.as_view(), name='invoice_cancel'),
    path('invoices/<int:pk>/payments/', views.PaymentCreateView.as_view(), name='invoice_payment_create'),

    path('patients/<int:pk>/invoices/', views.PatientInvoicesView.as_view(), name='patient_invoices'),

    path('payments/<int:pk>/receipt/', views.ReceiptPDFView.as_view(), name='payment_receipt'),
    path('payments/me/<int:pk>/receipt/', views.MyReceiptPDFView.as_view(), name='payment_receipt_mine'),
]
