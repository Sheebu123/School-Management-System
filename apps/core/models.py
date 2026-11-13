import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', _('Administrator')
    TEACHER = 'TEACHER', _('Teacher')
    GUARDIAN = 'GUARDIAN', _('Guardian')
    STUDENT = 'STUDENT', _('Student')


class User(AbstractUser):
    """
    Custom user model supporting multi-role authentication and authorization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.ADMIN,
        help_text=_('Designates the functional role and access tier of the user.')
    )
    phone_number = models.CharField(max_length=20, blank=True, default='')

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['date_joined']

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN or self.is_superuser

    @property
    def is_teacher(self):
        return self.role == UserRole.TEACHER

    @property
    def is_guardian(self):
        return self.role == UserRole.GUARDIAN

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username


class TeacherProfile(models.Model):
    """
    Profile metadata for teaching staff members.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    employee_id = models.CharField(max_length=30, unique=True, db_index=True)
    qualification = models.CharField(max_length=150, blank=True, default='')
    specialization = models.CharField(max_length=150, blank=True, default='')
    joining_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Teacher Profile')
        verbose_name_plural = _('Teacher Profiles')
        ordering = ['user__first_name', 'user__last_name']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"


class GuardianProfile(models.Model):
    """
    Profile metadata for parents and legal guardians.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='guardian_profile')
    relationship = models.CharField(max_length=50, default='Parent')
    occupation = models.CharField(max_length=100, blank=True, default='')
    emergency_contact = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = _('Guardian Profile')
        verbose_name_plural = _('Guardian Profiles')

    def __str__(self):
        return f"{self.user.get_full_name()} (Guardian)"


class StudentProfile(models.Model):
    """
    Core student entity linked to Guardian and optionally to a User account.
    """
    class Gender(models.TextChoices):
        MALE = 'M', _('Male')
        FEMALE = 'F', _('Female')
        OTHER = 'O', _('Other')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile'
    )
    admission_number = models.CharField(max_length=30, unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=Gender.choices, default=Gender.MALE)
    guardian = models.ForeignKey(
        GuardianProfile,
        on_delete=models.PROTECT,
        related_name='students',
        help_text=_('Guardian legally responsible for this student.')
    )
    address = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Student Profile')
        verbose_name_plural = _('Student Profiles')
        ordering = ['admission_number']

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.full_name} ({self.admission_number})"


class AuditLog(models.Model):
    """
    Immutable audit trail recording critical administrative, academic, and financial operations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_entries'
    )
    action = models.CharField(max_length=50, db_index=True)
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.CharField(max_length=100, blank=True, default='')
    description = models.TextField(blank=True, default='')
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        ordering = ['-timestamp']

    def __str__(self):
        actor_name = self.actor.username if self.actor else 'SYSTEM'
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {actor_name} -> {self.action} on {self.entity_type}"
