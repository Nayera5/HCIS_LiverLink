from django.urls import path

from . import views

# Mounted under /api/radiology/ in config/urls.py.
urlpatterns = [
    path("orders/", views.ImagingOrderListCreateView.as_view(), name="imaging_order_list"),
    path("orders/<int:pk>/", views.ImagingOrderDetailView.as_view(), name="imaging_order_detail"),
    path("orders/<int:pk>/status/", views.ImagingOrderStatusView.as_view(), name="imaging_order_status"),
    path("orders/<int:pk>/slots/", views.OrderSlotsView.as_view(), name="imaging_order_slots"),
    path("orders/<int:pk>/booking/", views.OrderBookingView.as_view(), name="imaging_booking"),
    path("orders/<int:pk>/booking/cancel/", views.OrderBookingView.as_view(action="cancel"),
         name="imaging_booking_cancel"),
    path("orders/<int:pk>/booking/no-show/", views.OrderBookingView.as_view(action="no_show"),
         name="imaging_booking_no_show"),
    path("orders/<int:pk>/remind/", views.OrderRemindView.as_view(), name="imaging_remind"),
    path("my-orders/", views.MyOrdersView.as_view(), name="my_imaging_orders"),
    path("my-orders/<int:pk>/slots/", views.MyOrderSlotsView.as_view(), name="my_imaging_slots"),
    path("my-orders/<int:pk>/booking/", views.MyOrderBookingView.as_view(), name="my_imaging_booking"),
    path("my-orders/<int:pk>/booking/cancel/", views.MyOrderBookingView.as_view(action="cancel"),
         name="my_imaging_booking_cancel"),
    path("slots/", views.ImagingSlotListCreateView.as_view(), name="imaging_slot_list"),
    path("slots/<int:pk>/", views.ImagingSlotDetailView.as_view(), name="imaging_slot_detail"),
]
