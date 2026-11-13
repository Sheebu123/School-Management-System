from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.translation import gettext_lazy as _
from .models import AttendanceSession, AttendanceRecord, AttendanceStatus, SessionType
from apps.academics.models import ClassSection, SubjectAssignment
from apps.core.services import log_audit_event


def verify_teacher_class_access(teacher_profile, class_section):
    """
    Ensures that a teacher is either the class teacher or assigned a subject in this section.
    """
    if not teacher_profile:
        return False
    is_class_teacher = (class_section.class_teacher_id == teacher_profile.id)
    is_subject_teacher = SubjectAssignment.objects.filter(
        class_section=class_section,
        teacher=teacher_profile
    ).exists()
    return is_class_teacher or is_subject_teacher


def record_attendance_session(
    class_section,
    date,
    recorded_by,
    records_data,
    session_type=SessionType.FULL_DAY,
    notes="",
    update_existing=False,
    request=None
):
    """
    Transaction-safe attendance recording service.
    - Enforces teacher assignment check (Acceptance Criteria 1).
    - Prevents or safely updates duplicate sessions (Acceptance Criteria 2).
    - records_data is a list of dicts: [{'student': StudentProfile, 'status': 'PRESENT', 'remarks': ''}]
    """
    # 1. Access verification
    actor_user = recorded_by.user if recorded_by else None
    if recorded_by and not (actor_user and (actor_user.is_superuser or actor_user.is_admin)):
        if not verify_teacher_class_access(recorded_by, class_section):
            raise PermissionDenied(
                _("You are not assigned to record attendance for %(section)s.") % {'section': class_section.display_name}
            )

    # 2. Check for duplicate session
    existing_session = AttendanceSession.objects.filter(
        class_section=class_section,
        date=date,
        session_type=session_type
    ).first()

    if existing_session and not update_existing:
        raise ValidationError(
            _("Attendance has already been recorded for %(section)s on %(date)s (%(session)s). "
              "Please edit the existing attendance register if updates are needed.") % {
                'section': class_section.display_name,
                'date': date,
                'session': session_type
            }
        )

    with transaction.atomic():
        if existing_session:
            session = existing_session
            session.recorded_by = recorded_by
            session.notes = notes
            session.save(update_fields=['recorded_by', 'notes'])
            action = 'UPDATE_ATTENDANCE'
        else:
            session = AttendanceSession.objects.create(
                class_section=class_section,
                date=date,
                session_type=session_type,
                recorded_by=recorded_by,
                notes=notes
            )
            action = 'RECORD_ATTENDANCE'

        # Record entries map
        existing_records_map = {r.student_id: r for r in session.records.all()}
        records_to_create = []
        records_to_update = []

        for item in records_data:
            student = item['student']
            status = item.get('status', AttendanceStatus.PRESENT)
            remarks = item.get('remarks', '')

            if student.id in existing_records_map:
                record = existing_records_map[student.id]
                if record.status != status or record.remarks != remarks:
                    record.status = status
                    record.remarks = remarks
                    records_to_update.append(record)
            else:
                records_to_create.append(
                    AttendanceRecord(
                        session=session,
                        student=student,
                        status=status,
                        remarks=remarks
                    )
                )

        if records_to_create:
            AttendanceRecord.objects.bulk_create(records_to_create)

        if records_to_update:
            AttendanceRecord.objects.bulk_update(records_to_update, fields=['status', 'remarks'])

        # Audit trail logging
        log_audit_event(
            actor=actor_user,
            action=action,
            entity_type='AttendanceSession',
            entity_id=session.id,
            description=f"{action} for {class_section.display_name} on {date}. Total students: {len(records_data)}",
            request=request
        )

    return session


def get_student_attendance_summary(student, academic_year=None):
    """
    Calculate high-level attendance metrics for a specific student.
    """
    records = AttendanceRecord.objects.filter(student=student)
    if academic_year:
        records = records.filter(session__class_section__academic_year=academic_year)

    total_sessions = records.count()
    if total_sessions == 0:
        return {
            'total_sessions': 0,
            'present_count': 0,
            'absent_count': 0,
            'late_count': 0,
            'excused_count': 0,
            'attendance_percentage': 0.0,
        }

    present_count = records.filter(status=AttendanceStatus.PRESENT).count()
    absent_count = records.filter(status=AttendanceStatus.ABSENT).count()
    late_count = records.filter(status=AttendanceStatus.LATE).count()
    excused_count = records.filter(status=AttendanceStatus.EXCUSED).count()

    # Percentage: (Present + Late + Excused) / Total * 100 or strict Present:
    # Standard practice: Present + Late (counted as attended)
    attended = present_count + late_count
    percentage = round((attended / total_sessions) * 100, 2)

    return {
        'total_sessions': total_sessions,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'excused_count': excused_count,
        'attendance_percentage': percentage,
    }
