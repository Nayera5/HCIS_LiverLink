from django.contrib import admin

from .models import ImagingOrder, ImagingSlot


@admin.register(ImagingOrder)
class ImagingOrderAdmin(admin.ModelAdmin):
    list_display = ("imaging_order_id", "patient", "billing_service", "status", "ordered_by", "order_date")
    list_filter = ("status",)
    raw_id_fields = ("patient", "encounter", "ordered_by")


@admin.register(ImagingSlot)
class ImagingSlotAdmin(admin.ModelAdmin):
    list_display = ("slot_id", "billing_service", "start_time", "end_time", "is_published", "created_by")
    list_filter = ("is_published",)
