from django.urls import path

from . import views

# Mounted under /api/ in config/urls.py.
urlpatterns = [
    path('hl7/messages/', views.HL7MessageListView.as_view(), name='hl7_message_list'),
    path('hl7/messages/<int:pk>/', views.HL7MessageDetailView.as_view(), name='hl7_message_detail'),
    path('hl7/messages/<int:pk>/resend/', views.HL7MessageResendView.as_view(), name='hl7_message_resend'),
]
