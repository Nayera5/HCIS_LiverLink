from django.contrib import admin

from .models import Diagnosis, Document, Encounter, EncounterAddendum, MedicalHistory, VitalSigns


class AddendumInline(admin.TabularInline):
    model = EncounterAddendum
    extra = 0
    readonly_fields = ("created_at",)


class DiagnosisInline(admin.TabularInline):
    model = Diagnosis
    extra = 0


class VitalSignsInline(admin.TabularInline):
    model = VitalSigns
    extra = 0
    readonly_fields = ("bmi",)


@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ("encounter_id", "patient", "staff", "encounter_date", "status")
    list_filter = ("status",)
    date_hierarchy = "encounter_date"
    inlines = [DiagnosisInline, VitalSignsInline, AddendumInline]


@admin.register(MedicalHistory)
class MedicalHistoryAdmin(admin.ModelAdmin):
    list_display = ("history_id", "patient", "history_type", "onset_date", "recorded_by")
    list_filter = ("history_type",)


@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ("diagnosis_id", "patient", "icd10_code", "description", "is_primary", "status")
    list_filter = ("status", "is_primary")
    search_fields = ("icd10_code", "description")


@admin.register(VitalSigns)
class VitalSignsAdmin(admin.ModelAdmin):
    list_display = ("vitals_id", "encounter", "bp_systolic", "bp_diastolic", "pulse", "bmi", "recorded_at")
    readonly_fields = ("bmi",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("document_id", "title", "patient", "document_type", "is_released", "uploaded_at")
    list_filter = ("document_type", "is_released")
    search_fields = ("title",)
