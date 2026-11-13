from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, TeacherProfile, GuardianProfile, StudentProfile, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active']
    list_filter = ['role', 'is_staff', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role Information', {'fields': ('role', 'phone_number')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role Information', {'fields': ('role', 'phone_number')}),
    )


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'employee_id', 'specialization', 'qualification', 'is_active']
    search_fields = ['user__first_name', 'user__last_name', 'employee_id', 'specialization']
    list_filter = ['is_active']


@admin.register(GuardianProfile)
class GuardianProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'relationship', 'occupation', 'emergency_contact']
    search_fields = ['user__first_name', 'user__last_name', 'emergency_contact']


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['admission_number', 'first_name', 'last_name', 'gender', 'guardian', 'is_active']
    search_fields = ['admission_number', 'first_name', 'last_name', 'guardian__user__first_name', 'guardian__user__last_name']
    list_filter = ['gender', 'is_active']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'actor', 'action', 'entity_type', 'entity_id', 'ip_address']
    list_filter = ['action', 'entity_type', 'timestamp']
    search_fields = ['entity_type', 'entity_id', 'description', 'actor__username']
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
