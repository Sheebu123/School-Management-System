import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TeacherProfile, StudentProfile


class AcademicYear(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, help_text=_('e.g., 2026-2027'))
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Academic Year')
        verbose_name_plural = _('Academic Years')
        ordering = ['-start_date']

    def __str__(self):
        current_badge = " (Current)" if self.is_current else ""
        return f"{self.name}{current_badge}"

    def save(self, *args, **kwargs):
        if self.is_current:
            # Enforce single current academic year
            AcademicYear.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class ClassLevel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, help_text=_('e.g., Grade 9, Grade 10'))
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = _('Class Level')
        verbose_name_plural = _('Class Levels')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class ClassSection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name='sections')
    section_name = models.CharField(max_length=20, help_text=_('e.g., A, B, Green'))
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name='sections')
    class_teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mentored_sections'
    )

    class Meta:
        verbose_name = _('Class Section')
        verbose_name_plural = _('Class Sections')
        constraints = [
            models.UniqueConstraint(
                fields=['class_level', 'section_name', 'academic_year'],
                name='unique_class_section_per_year'
            )
        ]
        ordering = ['class_level__order', 'section_name']

    @property
    def display_name(self):
        return f"{self.class_level.name} - {self.section_name} ({self.academic_year.name})"

    def __str__(self):
        return self.display_name


class Subject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True, help_text=_('e.g., MTH101'))
    name = models.CharField(max_length=100)
    is_elective = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Subject')
        verbose_name_plural = _('Subjects')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class SubjectAssignment(models.Model):
    """
    Assigns a teacher to instruct a subject in a specific class section.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name='subject_assignments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assignments')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.PROTECT, related_name='assigned_subjects')

    class Meta:
        verbose_name = _('Subject Assignment')
        verbose_name_plural = _('Subject Assignments')
        constraints = [
            models.UniqueConstraint(
                fields=['class_section', 'subject'],
                name='unique_subject_per_section'
            )
        ]

    def __str__(self):
        return f"{self.class_section.display_name} - {self.subject.name} ({self.teacher.user.get_full_name()})"


class StudentEnrollment(models.Model):
    """
    Links a student to a class section for an academic year.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(StudentProfile, on_delete=models.PROTECT, related_name='enrollments')
    class_section = models.ForeignKey(ClassSection, on_delete=models.PROTECT, related_name='enrollments')
    roll_number = models.PositiveIntegerField()
    enrollment_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Student Enrollment')
        verbose_name_plural = _('Student Enrollments')
        constraints = [
            models.UniqueConstraint(
                fields=['class_section', 'roll_number'],
                name='unique_roll_per_section'
            ),
            models.UniqueConstraint(
                fields=['student', 'class_section'],
                name='unique_student_section_enrollment'
            )
        ]
        ordering = ['class_section', 'roll_number']

    def __str__(self):
        return f"Roll {self.roll_number}: {self.student.full_name} in {self.class_section.display_name}"
