from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'title', 'channel', 'is_read', 'sent_at']
    list_filter = ['type', 'channel', 'is_read']
    search_fields = ['user__username', 'title', 'message']
    autocomplete_fields = ['user']
