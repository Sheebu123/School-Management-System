import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TeacherProfile, StudentProfile
from apps.academics.models import ClassSection


class AttendanceStatus(models.TextChoices):
    PRESENT = 'PRESENT', _('Present')
    ABSENT = 'ABSENT', _('Absent')
    LATE = 'LATE', _('Late')
    EXCUSED = 'EXCUSED', _('Excused')


class SessionType(models.TextChoices):
    FULL_DAY = 'FULL_DAY', _('Full Day')
    MORNING = 'MORNING', _('Morning')
    AFTERNOON = 'AFTERNOON', _('Afternoon')


class AttendanceSession(models.Model):
    """
    Header record representing an attendance session for a class section on a given date.
    Strict unique constraint prevents duplicate session creation for the same section/date/session_type.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name='attendance_sessions'
    )
    date = models.DateField(db_index=True)
    session_type = models.CharField(
        max_length=20,
        choices=SessionType.choices,
        default=SessionType.FULL_DAY
    )
    recorded_by = models.ForeignKey(
        TeacherProfile,
        on_delete=models.PROTECT,
        related_name='recorded_attendance_sessions'
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = _('Attendance Session')
        verbose_name_plural = _('Attendance Sessions')
        constraints = [
            models.UniqueConstraint(
                fields=['class_section', 'date', 'session_type'],
                name='unique_attendance_session'
            )
        ]
        ordering = ['-date', 'class_section']

    def __str__(self):
        return f"{self.class_section.display_name} - {self.date} ({self.get_session_type_display()})"


class AttendanceRecord(models.Model):
    """
    Individual student attendance entry within an AttendanceSession.
    Enforces uniqueness per student per session to guarantee no duplicate roll calls.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name='records'
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name='attendance_records'
    )
    status = models.CharField(
        max_length=15,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT
    )
    remarks = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        verbose_name = _('Attendance Record')
        verbose_name_plural = _('Attendance Records')
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'student'],
                name='unique_attendance_per_student_session'
            )
        ]
        indexes = [
            models.Index(fields=['student', 'status'], name='student_attendance_status_idx'),
        ]

    def __str__(self):
        return f"{self.student.full_name}: {self.get_status_display()} ({self.session.date})"
