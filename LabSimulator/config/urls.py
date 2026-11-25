from django.urls import path

from lis import views

urlpatterns = [
    path('', views.index),
    path('api/orders/', views.order_list),
    path('api/orders/<int:pk>/', views.order_detail),
    path('api/orders/<int:pk>/status/', views.change_status),
    path('api/orders/<int:pk>/results/', views.save_results),
    path('api/orders/<int:pk>/send/', views.send_results),
    path('api/messages/', views.message_list),
    path('api/messages/<int:pk>/', views.message_detail),
]
