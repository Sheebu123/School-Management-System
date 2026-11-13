from django.contrib import admin
from .models import AcademicYear, ClassLevel, ClassSection, Subject, SubjectAssignment, StudentEnrollment


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_current']
    list_filter = ['is_current']


@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    list_display = ['name', 'order']
    ordering = ['order']


@admin.register(ClassSection)
class ClassSectionAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'class_level', 'section_name', 'academic_year', 'class_teacher']
    list_filter = ['academic_year', 'class_level']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_elective']
    search_fields = ['name', 'code']


@admin.register(SubjectAssignment)
class SubjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ['class_section', 'subject', 'teacher']
    list_filter = ['class_section__academic_year', 'teacher']


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['roll_number', 'student', 'class_section', 'is_active']
    list_filter = ['class_section__academic_year', 'class_section', 'is_active']
    search_fields = ['student__first_name', 'student__last_name', 'student__admission_number']
