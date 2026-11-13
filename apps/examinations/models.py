import uuid
from decimal import Decimal
from django.db import models
from django.db.models import Q, F
from django.utils.translation import gettext_lazy as _
from apps.core.models import StudentProfile
from apps.academics.models import AcademicYear, SubjectAssignment


class GradingSystem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text=_('e.g., Standard 10-Point Scale'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Grading System')
        verbose_name_plural = _('Grading Systems')

    def __str__(self):
        return self.name


class GradeRule(models.Model):
    """
    Configurable grading thresholds (min_percentage to max_percentage) -> grade letter & point.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grading_system = models.ForeignKey(GradingSystem, on_delete=models.CASCADE, related_name='rules')
    grade_letter = models.CharField(max_length=5, help_text=_('e.g., A+, A, B, C, D, F'))
    grade_point = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.00'))
    min_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text=_('Inclusive minimum %'))
    max_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text=_('Inclusive maximum %'))
    description = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        verbose_name = _('Grade Rule')
        verbose_name_plural = _('Grade Rules')
        ordering = ['-min_percentage']
        constraints = [
            models.CheckConstraint(
                condition=Q(min_percentage__lte=F('max_percentage')),
                name='valid_percentage_range'
            )
        ]

    def __str__(self):
        return f"{self.grade_letter} ({self.min_percentage}% - {self.max_percentage}%) [GP: {self.grade_point}]"


class Exam(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text=_('e.g., Term 1 Examination 2026'))
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name='exams')
    grading_system = models.ForeignKey(GradingSystem, on_delete=models.PROTECT, related_name='exams')
    start_date = models.DateField()
    end_date = models.DateField()
    is_published = models.BooleanField(default=False, help_text=_('If true, results are visible to guardians.'))

    class Meta:
        verbose_name = _('Examination')
        verbose_name_plural = _('Examinations')
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name} ({self.academic_year.name})"


class ExamSubjectSchedule(models.Model):
    """
    Schedules an exam for a specific subject assignment in a class section.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='schedules')
    subject_assignment = models.ForeignKey(SubjectAssignment, on_delete=models.CASCADE, related_name='exam_schedules')
    exam_date = models.DateField()
    max_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('100.00'))
    passing_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('40.00'))

    class Meta:
        verbose_name = _('Exam Subject Schedule')
        verbose_name_plural = _('Exam Subject Schedules')
        constraints = [
            models.UniqueConstraint(
                fields=['exam', 'subject_assignment'],
                name='unique_exam_subject_assignment'
            )
        ]
        ordering = ['exam_date']

    def __str__(self):
        return f"{self.exam.name} - {self.subject_assignment.class_section.display_name} - {self.subject_assignment.subject.name}"


class StudentMark(models.Model):
    """
    Subject marks recorded for an individual student.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam_schedule = models.ForeignKey(ExamSubjectSchedule, on_delete=models.CASCADE, related_name='marks')
    student = models.ForeignKey(StudentProfile, on_delete=models.PROTECT, related_name='exam_marks')
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    is_absent = models.BooleanField(default=False)
    remarks = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        verbose_name = _('Student Mark')
        verbose_name_plural = _('Student Marks')
        constraints = [
            models.UniqueConstraint(
                fields=['exam_schedule', 'student'],
                name='unique_mark_per_student_schedule'
            ),
            models.CheckConstraint(
                condition=Q(marks_obtained__gte=0),
                name='mark_non_negative'
            )
        ]

    def __str__(self):
        status = "ABSENT" if self.is_absent else f"{self.marks_obtained}/{self.exam_schedule.max_marks}"
        return f"{self.student.full_name} - {self.exam_schedule.subject_assignment.subject.name}: {status}"
