from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from rest_framework import permissions
from .models import UserRole


class RoleRequiredMixin(AccessMixin):
    """
    CBV mixin to restrict access to specific roles.
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        if request.user.role not in self.allowed_roles:
            raise PermissionDenied("You do not have permission to access this resource.")

        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = [UserRole.ADMIN]


class TeacherRequiredMixin(RoleRequiredMixin):
    allowed_roles = [UserRole.TEACHER, UserRole.ADMIN]


class GuardianRequiredMixin(RoleRequiredMixin):
    allowed_roles = [UserRole.GUARDIAN, UserRole.ADMIN]


class GuardianStudentAccessMixin(GuardianRequiredMixin):
    """
    Verifies that the requested student belongs to the authenticated guardian (IDOR protection).
    """
    def check_ward_access(self, student_id):
        user = self.request.user
        if user.is_superuser or user.role == UserRole.ADMIN:
            return True
        if not hasattr(user, 'guardian_profile'):
            raise PermissionDenied("Guardian profile not found.")
        is_ward = user.guardian_profile.students.filter(id=student_id).exists()
        if not is_ward:
            raise PermissionDenied("You do not have permission to view data for this student.")
        return True


# DRF REST API Permissions
class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.is_admin or request.user.is_superuser))


class IsTeacherRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.is_teacher or request.user.is_admin or request.user.is_superuser))


class IsGuardianRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.is_guardian or request.user.is_admin or request.user.is_superuser))


class IsGuardianOfStudentObject(permissions.BasePermission):
    """
    Object-level permission ensuring guardian can only access their own linked wards.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin or request.user.is_superuser:
            return True
        if not hasattr(request.user, 'guardian_profile'):
            return False

        # Support checking against StudentProfile directly or objects with a 'student' foreign key
        student = obj if hasattr(obj, 'admission_number') else getattr(obj, 'student', None)
        if not student:
            return False
        return student.guardian_id == request.user.guardian_profile.id
