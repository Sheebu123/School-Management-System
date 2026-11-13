from django.contrib import admin
from .models import AttendanceSession, AttendanceRecord


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    autocomplete_fields = ['student']


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ['class_section', 'date', 'session_type', 'recorded_by', 'recorded_at']
    list_filter = ['session_type', 'date', 'class_section__academic_year']
    inlines = [AttendanceRecordInline]


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['session', 'student', 'status', 'remarks']
    list_filter = ['status', 'session__date']
    search_fields = ['student__first_name', 'student__last_name', 'student__admission_number']
