import pytest
from datetime import date
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.attendance.services import record_attendance_session
from apps.attendance.models import AttendanceSession, AttendanceRecord, AttendanceStatus, SessionType


@pytest.mark.django_db
class TestDuplicateAttendancePrevention:
    """
    Acceptance Criteria 2:
    Duplicate attendance for the same student/session is rejected or safely handled.
    """

    def test_duplicate_session_submission_raises_validation_error(self, db_setup):
        teacher_1 = db_setup['teacher_1']
        section_10a = db_setup['section_10a']
        student_1 = db_setup['student_1']
        session_date = date(2026, 11, 13)

        # 1. Initial successful attendance submission
        session_1 = record_attendance_session(
            class_section=section_10a,
            date=session_date,
            recorded_by=teacher_1,
            records_data=[{'student': student_1, 'status': AttendanceStatus.PRESENT}]
        )
        assert session_1 is not None
        assert AttendanceSession.objects.filter(class_section=section_10a, date=session_date).count() == 1

        # 2. Attempting identical submission without update flag must raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            record_attendance_session(
                class_section=section_10a,
                date=session_date,
                recorded_by=teacher_1,
                records_data=[{'student': student_1, 'status': AttendanceStatus.PRESENT}],
                update_existing=False
            )
        assert "Attendance has already been recorded" in str(exc_info.value)

        # Assert count remains strictly 1
        assert AttendanceSession.objects.filter(class_section=section_10a, date=session_date).count() == 1

    def test_safe_update_of_existing_attendance_session(self, db_setup):
        teacher_1 = db_setup['teacher_1']
        section_10a = db_setup['section_10a']
        student_1 = db_setup['student_1']
        session_date = date(2026, 11, 13)

        # Initial: Present
        session = record_attendance_session(
            class_section=section_10a,
            date=session_date,
            recorded_by=teacher_1,
            records_data=[{'student': student_1, 'status': AttendanceStatus.PRESENT}]
        )
        assert session.records.first().status == AttendanceStatus.PRESENT

        # Update: Changed to Absent with update_existing=True
        updated_session = record_attendance_session(
            class_section=section_10a,
            date=session_date,
            recorded_by=teacher_1,
            records_data=[{'student': student_1, 'status': AttendanceStatus.ABSENT, 'remarks': 'Doctor visit'}],
            update_existing=True
        )

        assert updated_session.id == session.id
        # Assert no duplicate session created
        assert AttendanceSession.objects.filter(class_section=section_10a, date=session_date).count() == 1
        # Assert no duplicate record created
        assert AttendanceRecord.objects.filter(session=session, student=student_1).count() == 1
        rec = AttendanceRecord.objects.get(session=session, student=student_1)
        assert rec.status == AttendanceStatus.ABSENT
        assert rec.remarks == 'Doctor visit'

    def test_database_level_unique_constraint_on_student_session(self, db_setup):
        teacher_1 = db_setup['teacher_1']
        section_10a = db_setup['section_10a']
        student_1 = db_setup['student_1']
        session_date = date(2026, 11, 14)

        session = AttendanceSession.objects.create(
            class_section=section_10a,
            date=session_date,
            recorded_by=teacher_1,
            session_type=SessionType.FULL_DAY
        )
        AttendanceRecord.objects.create(
            session=session,
            student=student_1,
            status=AttendanceStatus.PRESENT
        )

        # Attempting direct insert of another record for same student and session violates DB UniqueConstraint
        with pytest.raises(IntegrityError):
            AttendanceRecord.objects.create(
                session=session,
                student=student_1,
                status=AttendanceStatus.ABSENT
            )

    def test_database_level_unique_constraint_on_session(self, db_setup):
        teacher_1 = db_setup['teacher_1']
        section_10a = db_setup['section_10a']
        session_date = date(2026, 11, 15)

        AttendanceSession.objects.create(
            class_section=section_10a,
            date=session_date,
            recorded_by=teacher_1,
            session_type=SessionType.FULL_DAY
        )

        # Direct duplicate session creation violates DB UniqueConstraint
        with pytest.raises(IntegrityError):
            AttendanceSession.objects.create(
                class_section=section_10a,
                date=session_date,
                recorded_by=teacher_1,
                session_type=SessionType.FULL_DAY
            )
