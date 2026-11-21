from django.contrib import admin

from .models import DonorApplication, MRNSequence, Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('mrn', 'first_name', 'last_name', 'category', 'sex', 'date_of_birth', 'created_at')
    list_filter = ('category', 'sex', 'blood_group')
    search_fields = ('mrn', 'national_id', 'first_name', 'last_name', 'phone')
    readonly_fields = ('mrn', 'created_at', 'updated_at')
    raw_id_fields = ('user', 'registered_by')


@admin.register(DonorApplication)
class DonorApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'donor', 'recipient', 'relationship', 'status', 'submitted_at', 'screened_at')
    list_filter = ('status',)
    search_fields = ('donor__mrn', 'recipient__mrn', 'donor__last_name', 'recipient__last_name')
    readonly_fields = ('submitted_at', 'updated_at')
    raw_id_fields = ('donor', 'recipient', 'screened_by')


@admin.register(MRNSequence)
class MRNSequenceAdmin(admin.ModelAdmin):
    """Visible for support only; the counter must never be edited by hand."""

    list_display = ('id', 'last_value')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
