from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.translation import gettext_lazy as _
from .models import GradeRule, StudentMark, ExamSubjectSchedule
from apps.core.services import log_audit_event


def get_grade_for_percentage(percentage, grading_system):
    """
    Evaluates dynamic GradeRules for a given percentage and returns:
    (grade_letter, grade_point, description)
    """
    if grading_system is None:
        return 'N/A', Decimal('0.00'), ''

    # Decimal conversion and rounding
    pct = Decimal(str(percentage)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    rules = grading_system.rules.order_by('-min_percentage')
    for rule in rules:
        if rule.min_percentage <= pct <= rule.max_percentage:
            return rule.grade_letter, rule.grade_point, rule.description

    # Fallback if percentage is below lowest rule min
    lowest_rule = rules.last()
    if lowest_rule and pct < lowest_rule.min_percentage:
        return lowest_rule.grade_letter, lowest_rule.grade_point, lowest_rule.description

    return 'F', Decimal('0.00'), 'Fail'


def generate_student_report_card(student, exam):
    """
    Generates a calculated report card for a student in a specific exam.
    Returns:
    {
        'student': student,
        'exam': exam,
        'subject_results': [...],
        'total_obtained': Decimal,
        'total_max': Decimal,
        'aggregate_percentage': Decimal,
        'overall_grade': str,
        'gpa': Decimal,
        'status': 'PASSED' / 'FAILED',
        'has_marks': bool
    }
    """
    marks_records = StudentMark.objects.filter(
        student=student,
        exam_schedule__exam=exam
    ).select_related('exam_schedule__subject_assignment__subject', 'exam_schedule__exam__grading_system')

    if not marks_records.exists():
        return {
            'student': student,
            'exam': exam,
            'subject_results': [],
            'total_obtained': Decimal('0.00'),
            'total_max': Decimal('0.00'),
            'aggregate_percentage': Decimal('0.00'),
            'overall_grade': 'N/A',
            'gpa': Decimal('0.00'),
            'status': 'NO_DATA',
            'has_marks': False
        }

    grading_system = exam.grading_system
    subject_results = []
    total_obtained = Decimal('0.00')
    total_max = Decimal('0.00')
    total_grade_points = Decimal('0.00')
    any_failed = False

    for record in marks_records:
        sched = record.exam_schedule
        subject = sched.subject_assignment.subject
        max_m = sched.max_marks
        pass_m = sched.passing_marks

        if record.is_absent:
            obt_m = Decimal('0.00')
            pct = Decimal('0.00')
            grade_letter = 'AB'
            grade_point = Decimal('0.00')
            is_passed = False
            any_failed = True
        else:
            obt_m = record.marks_obtained
            pct = ((obt_m / max_m) * Decimal('100.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if max_m > 0 else Decimal('0.00')
            grade_letter, grade_point, _ = get_grade_for_percentage(pct, grading_system)
            is_passed = (obt_m >= pass_m)
            if not is_passed:
                any_failed = True

        total_obtained += obt_m
        total_max += max_m
        total_grade_points += grade_point

        subject_results.append({
            'subject_name': subject.name,
            'subject_code': subject.code,
            'max_marks': max_m,
            'passing_marks': pass_m,
            'marks_obtained': obt_m,
            'is_absent': record.is_absent,
            'percentage': pct,
            'grade_letter': grade_letter,
            'grade_point': grade_point,
            'is_passed': is_passed,
            'remarks': record.remarks
        })

    subject_count = len(subject_results)
    aggregate_pct = ((total_obtained / total_max) * Decimal('100.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if total_max > 0 else Decimal('0.00')
    gpa = (total_grade_points / Decimal(str(subject_count))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if subject_count > 0 else Decimal('0.00')
    overall_grade, _, _ = get_grade_for_percentage(aggregate_pct, grading_system)

    overall_status = 'FAILED' if any_failed else 'PASSED'

    return {
        'student': student,
        'exam': exam,
        'subject_results': subject_results,
        'total_obtained': total_obtained,
        'total_max': total_max,
        'aggregate_percentage': aggregate_pct,
        'overall_grade': overall_grade,
        'gpa': gpa,
        'status': overall_status,
        'has_marks': True
    }


def bulk_save_subject_marks(exam_schedule, marks_data, teacher_profile=None, request=None):
    """
    Transaction-safe bulk marks entry service.
    Verifies teacher assignment and bounds check (0 <= mark <= max_marks).
    marks_data: [{'student': StudentProfile, 'marks_obtained': Decimal, 'is_absent': bool, 'remarks': ''}]
    """
    # 1. Permission check
    if teacher_profile:
        user = teacher_profile.user
        if not (user.is_superuser or user.is_admin):
            assigned_teacher = exam_schedule.subject_assignment.teacher
            if assigned_teacher.id != teacher_profile.id:
                raise PermissionDenied(
                    _("You are not assigned to record marks for %(subject)s in %(section)s.") % {
                        'subject': exam_schedule.subject_assignment.subject.name,
                        'section': exam_schedule.subject_assignment.class_section.display_name
                    }
                )

    max_marks = exam_schedule.max_marks

    # 2. Validation & atomic commit
    with transaction.atomic():
        existing_marks_map = {m.student_id: m for m in exam_schedule.marks.all()}
        marks_to_create = []
        marks_to_update = []

        for item in marks_data:
            student = item['student']
            is_absent = item.get('is_absent', False)
            obt = Decimal(str(item.get('marks_obtained', 0))) if not is_absent else Decimal('0.00')
            remarks = item.get('remarks', '')

            if not is_absent:
                if obt < 0:
                    raise ValidationError(_("Marks obtained cannot be negative for %(student)s.") % {'student': student.full_name})
                if obt > max_marks:
                    raise ValidationError(
                        _("Marks obtained (%(obt)s) cannot exceed maximum marks (%(max)s) for %(student)s.") % {
                            'obt': obt, 'max': max_marks, 'student': student.full_name
                        }
                    )

            if student.id in existing_marks_map:
                mark_rec = existing_marks_map[student.id]
                mark_rec.marks_obtained = obt
                mark_rec.is_absent = is_absent
                mark_rec.remarks = remarks
                marks_to_update.append(mark_rec)
            else:
                marks_to_create.append(
                    StudentMark(
                        exam_schedule=exam_schedule,
                        student=student,
                        marks_obtained=obt,
                        is_absent=is_absent,
                        remarks=remarks
                    )
                )

        if marks_to_create:
            StudentMark.objects.bulk_create(marks_to_create)

        if marks_to_update:
            StudentMark.objects.bulk_update(marks_to_update, fields=['marks_obtained', 'is_absent', 'remarks'])

        log_audit_event(
            actor=teacher_profile.user if teacher_profile else None,
            action='ENTER_EXAM_MARKS',
            entity_type='ExamSubjectSchedule',
            entity_id=exam_schedule.id,
            description=f"Recorded marks for {exam_schedule.subject_assignment.subject.name} ({exam_schedule.exam.name}). Students evaluated: {len(marks_data)}",
            request=request
        )

    return True
