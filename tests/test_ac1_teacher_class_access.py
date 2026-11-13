import pytest
from datetime import date
from django.core.exceptions import PermissionDenied
from apps.attendance.services import record_attendance_session, verify_teacher_class_access
from apps.attendance.models import AttendanceStatus, AttendanceSession


@pytest.mark.django_db
class TestTeacherClassAccess:
    """
    Acceptance Criteria 1:
    Teachers can access only their assigned classes and record attendance.
    """

    def test_teacher_assigned_can_record_attendance(self, db_setup):
        teacher_1 = db_setup['teacher_1']
        section_10a = db_setup['section_10a']
        student_1 = db_setup['student_1']

        # Verify teacher 1 has access to section 10-A
        assert verify_teacher_class_access(teacher_1, section_10a) is True

        # Teacher 1 successfully records attendance for 10-A
        session = record_attendance_session(
            class_section=section_10a,
            date=date(2026, 11, 13),
            recorded_by=teacher_1,
            records_data=[{'student': student_1, 'status': AttendanceStatus.PRESENT}]
        )
        assert session is not None
        assert session.records.count() == 1
        assert session.records.first().status == AttendanceStatus.PRESENT

    def test_teacher_unassigned_is_forbidden_from_recording_attendance(self, db_setup):
        teacher_1 = db_setup['teacher_1']
        section_10b = db_setup['section_10b']  # Teacher 1 is NOT assigned to 10-B
        student_2 = db_setup['student_2']

        # Verify teacher 1 has NO access to section 10-B
        assert verify_teacher_class_access(teacher_1, section_10b) is False

        # Attempting to record attendance must raise PermissionDenied
        with pytest.raises(PermissionDenied):
            record_attendance_session(
                class_section=section_10b,
                date=date(2026, 11, 13),
                recorded_by=teacher_1,
                records_data=[{'student': student_2, 'status': AttendanceStatus.PRESENT}]
            )

        # Assert no session was created in the database for 10-B
        assert not AttendanceSession.objects.filter(class_section=section_10b).exists()

    def test_teacher_2_can_record_for_10b_but_rejected_for_10a(self, db_setup):
        teacher_2 = db_setup['teacher_2']
        section_10a = db_setup['section_10a']
        section_10b = db_setup['section_10b']
        student_2 = db_setup['student_2']
        student_1 = db_setup['student_1']

        # Teacher 2 assigned to 10-B: Success
        session = record_attendance_session(
            class_section=section_10b,
            date=date(2026, 11, 13),
            recorded_by=teacher_2,
            records_data=[{'student': student_2, 'status': AttendanceStatus.PRESENT}]
        )
        assert session is not None
        assert session.records.count() == 1

        # Teacher 2 attempting for 10-A: Forbidden
        with pytest.raises(PermissionDenied):
            record_attendance_session(
                class_section=section_10a,
                date=date(2026, 11, 14),
                recorded_by=teacher_2,
                records_data=[{'student': student_1, 'status': AttendanceStatus.PRESENT}]
            )
