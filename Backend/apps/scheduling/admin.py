from django.contrib import admin

from .models import Appointment, DoctorSchedule


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ("schedule_id", "staff", "day_of_week", "start_time", "end_time", "slot_minutes", "is_active")
    list_filter = ("day_of_week", "is_active")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("appointment_id", "patient", "staff", "appointment_type", "start_time", "status")
    list_filter = ("status", "appointment_type")
    search_fields = ("patient__mrn", "patient__first_name", "patient__last_name")
