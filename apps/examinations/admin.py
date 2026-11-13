from django.contrib import admin
from .models import GradingSystem, GradeRule, Exam, ExamSubjectSchedule, StudentMark


class GradeRuleInline(admin.TabularInline):
    model = GradeRule
    extra = 1


@admin.register(GradingSystem)
class GradingSystemAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    inlines = [GradeRuleInline]


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['name', 'academic_year', 'grading_system', 'start_date', 'end_date', 'is_published']
    list_filter = ['academic_year', 'is_published']


@admin.register(ExamSubjectSchedule)
class ExamSubjectScheduleAdmin(admin.ModelAdmin):
    list_display = ['exam', 'subject_assignment', 'exam_date', 'max_marks', 'passing_marks']
    list_filter = ['exam', 'exam_date']


@admin.register(StudentMark)
class StudentMarkAdmin(admin.ModelAdmin):
    list_display = ['student', 'exam_schedule', 'marks_obtained', 'is_absent']
    list_filter = ['is_absent', 'exam_schedule__exam']
    search_fields = ['student__first_name', 'student__last_name', 'student__admission_number']
