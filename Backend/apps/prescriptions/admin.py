from django.contrib import admin

from .models import Drug, Prescription, TreatmentPlan


@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'generic_name', 'drug_class', 'default_route', 'is_active')
    list_filter = ('is_active', 'drug_class')
    search_fields = ('code', 'name', 'generic_name')
    readonly_fields = ('code', 'created_by', 'created_at')


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'drug', 'dose', 'route', 'frequency', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'route')
    raw_id_fields = ('patient', 'prescribed_by', 'drug')


@admin.register(TreatmentPlan)
class TreatmentPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'plan_type', 'start_date', 'review_date', 'status')
    list_filter = ('status', 'plan_type')
    raw_id_fields = ('patient', 'created_by')
