import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from apps.core.permissions import GuardianStudentAccessMixin, IsGuardianOfStudentObject
from apps.core.models import StudentProfile


@pytest.mark.django_db
class TestGuardianDataIsolation:
    """
    Acceptance Criteria 4:
    Guardians can see only the information belonging to their linked students (IDOR protection).
    """

    def test_guardian_can_access_own_ward(self, db_setup):
        guardian_1 = db_setup['guardian_1']
        student_1 = db_setup['student_1']

        factory = RequestFactory()
        request = factory.get('/')
        request.user = guardian_1.user

        mixin = GuardianStudentAccessMixin()
        mixin.request = request

        # Guardian 1 accessing own ward Student 1 succeeds
        assert mixin.check_ward_access(student_1.id) is True

    def test_guardian_cannot_access_unlinked_student_idor(self, db_setup):
        guardian_1 = db_setup['guardian_1']
        student_2 = db_setup['student_2']  # Belongs to Guardian 2

        factory = RequestFactory()
        request = factory.get('/')
        request.user = guardian_1.user

        mixin = GuardianStudentAccessMixin()
        mixin.request = request

        # Guardian 1 attempting to access Student 2 raises PermissionDenied (IDOR defense)
        with pytest.raises(PermissionDenied):
            mixin.check_ward_access(student_2.id)

    def test_guardian_queryset_filtering_contains_only_linked_wards(self, db_setup):
        guardian_1 = db_setup['guardian_1']
        student_1 = db_setup['student_1']
        student_2 = db_setup['student_2']

        # Enforce queryset scoping at repository level
        guardian_wards = StudentProfile.objects.filter(guardian=guardian_1)

        assert student_1 in guardian_wards
        assert student_2 not in guardian_wards
        assert guardian_wards.count() == 1

    def test_drf_guardian_object_permission_enforcement(self, db_setup):
        guardian_1 = db_setup['guardian_1']
        guardian_2 = db_setup['guardian_2']
        student_1 = db_setup['student_1']
        student_2 = db_setup['student_2']

        permission = IsGuardianOfStudentObject()
        factory = RequestFactory()

        # Request by Guardian 1 for Student 1: Allowed
        req1 = factory.get('/')
        req1.user = guardian_1.user
        assert permission.has_object_permission(req1, None, student_1) is True

        # Request by Guardian 1 for Student 2: Denied
        assert permission.has_object_permission(req1, None, student_2) is False

        # Request by Guardian 2 for Student 2: Allowed
        req2 = factory.get('/')
        req2.user = guardian_2.user
        assert permission.has_object_permission(req2, None, student_2) is True

        # Request by Guardian 2 for Student 1: Denied
        assert permission.has_object_permission(req2, None, student_1) is False
