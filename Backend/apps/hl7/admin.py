from django.contrib import admin

from .models import ExternalSystem


@admin.register(ExternalSystem)
class ExternalSystemAdmin(admin.ModelAdmin):
    list_display = ['name', 'system_type', 'host', 'port', 'is_active']
