from django.contrib import admin

from .models import LabOrder, LabResult, LabTest


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'unit', 'normal_min', 'normal_max', 'critical_min', 'critical_max')
    search_fields = ('code', 'name')


class LabResultInline(admin.TabularInline):
    model = LabResult
    extra = 0
    raw_id_fields = ('lab_test',)


@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'ordered_by', 'priority', 'status', 'order_date')
    list_filter = ('status', 'priority')
    raw_id_fields = ('patient', 'ordered_by')
    inlines = [LabResultInline]
