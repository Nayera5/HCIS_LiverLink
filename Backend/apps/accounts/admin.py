from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm

from .models import AuditLog, Staff, User


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only: audit entries are append-only (no add, change or delete, even for superusers)."""

    list_display = ('timestamp', 'user', 'action', 'entity_type', 'entity_id', 'patient', 'ip_address')
    list_filter = ('action', 'entity_type')
    search_fields = ('user__username', 'patient__mrn', 'entity_type')
    date_hierarchy = 'timestamp'
    list_select_related = ('user', 'patient')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StaffInline(admin.StackedInline):
    model = Staff
    can_delete = False
    extra = 0
    max_num = 1
    fields = ('job_title', 'department', 'license_no', 'phone')


class UserCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ('username', 'role')


class UserChangeForm(DjangoUserChangeForm):
    class Meta(DjangoUserChangeForm.Meta):
        model = User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Django's standard user admin, with LiverLink's `role` kept apart from admin-site access."""

    form = UserChangeForm
    add_form = UserCreationForm
    inlines = (StaffInline,)

    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'groups')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('LiverLink access', {'fields': ('role',)}),
        (
            'Django admin site access',
            {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')},
        ),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('username', 'role', 'usable_password', 'password1', 'password2'),
            },
        ),
    )


