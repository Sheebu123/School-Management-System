import pytest
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.examinations.models import Exam, ExamSubjectSchedule, StudentMark
from apps.examinations.services import (
    get_grade_for_percentage,
    generate_student_report_card,
    bulk_save_subject_marks
)


@pytest.mark.django_db
class TestGradingEngine:
    """
    Acceptance Criteria 3:
    Examination results are correctly calculated using configured grading rules.
    """

    def test_grading_rule_boundary_evaluations(self, db_setup):
        gs = db_setup['grading_system']

        # Boundary test: A+ (90.00 - 100.00)
        grade, gp, _ = get_grade_for_percentage(Decimal('100.00'), gs)
        assert grade == 'A+' and gp == Decimal('10.00')

        grade, gp, _ = get_grade_for_percentage(Decimal('90.00'), gs)
        assert grade == 'A+' and gp == Decimal('10.00')

        # Boundary test: A (80.00 - 89.99)
        grade, gp, _ = get_grade_for_percentage(Decimal('89.99'), gs)
        assert grade == 'A' and gp == Decimal('9.00')

        grade, gp, _ = get_grade_for_percentage(Decimal('80.00'), gs)
        assert grade == 'A' and gp == Decimal('9.00')

        # Boundary test: B (70.00 - 79.99)
        grade, gp, _ = get_grade_for_percentage(Decimal('75.50'), gs)
        assert grade == 'B' and gp == Decimal('8.00')

        # Boundary test: C (50.00 - 69.99)
        grade, gp, _ = get_grade_for_percentage(Decimal('50.00'), gs)
        assert grade == 'C' and gp == Decimal('6.00')

        # Boundary test: D (40.00 - 49.99)
        grade, gp, _ = get_grade_for_percentage(Decimal('40.00'), gs)
        assert grade == 'D' and gp == Decimal('4.00')

        # Boundary test: F (< 40.00)
        grade, gp, _ = get_grade_for_percentage(Decimal('39.99'), gs)
        assert grade == 'F' and gp == Decimal('0.00')

        grade, gp, _ = get_grade_for_percentage(Decimal('0.00'), gs)
        assert grade == 'F' and gp == Decimal('0.00')

    def test_report_card_aggregate_and_gpa_calculation(self, db_setup):
        acad_year = db_setup['acad_year']
        gs = db_setup['grading_system']
        student_1 = db_setup['student_1']
        assign_10a_math = db_setup['assign_10a_math']
        science = db_setup['science']
        section_10a = db_setup['section_10a']
        teacher_1 = db_setup['teacher_1']

        # Add science assignment to 10-A
        from apps.academics.models import SubjectAssignment
        assign_10a_sci = SubjectAssignment.objects.create(
            class_section=section_10a,
            subject=science,
            teacher=teacher_1
        )

        # Create Exam
        exam = Exam.objects.create(
            name='Midterm Exam 2026',
            academic_year=acad_year,
            grading_system=gs,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 10),
            is_published=True
        )

        # Schedule Math (Max 100, Pass 40)
        sched_math = ExamSubjectSchedule.objects.create(
            exam=exam,
            subject_assignment=assign_10a_math,
            exam_date=date(2026, 10, 2),
            max_marks=Decimal('100.00'),
            passing_marks=Decimal('40.00')
        )
        # Schedule Science (Max 100, Pass 40)
        sched_sci = ExamSubjectSchedule.objects.create(
            exam=exam,
            subject_assignment=assign_10a_sci,
            exam_date=date(2026, 10, 4),
            max_marks=Decimal('100.00'),
            passing_marks=Decimal('40.00')
        )

        # Student 1 gets 95 in Math, 85 in Science
        StudentMark.objects.create(exam_schedule=sched_math, student=student_1, marks_obtained=Decimal('95.00'))
        StudentMark.objects.create(exam_schedule=sched_sci, student=student_1, marks_obtained=Decimal('85.00'))

        report = generate_student_report_card(student_1, exam)

        assert report['has_marks'] is True
        assert report['total_obtained'] == Decimal('180.00')
        assert report['total_max'] == Decimal('200.00')
        # Aggregate percentage: (180/200)*100 = 90.00%
        assert report['aggregate_percentage'] == Decimal('90.00')
        # Overall grade for 90% is A+
        assert report['overall_grade'] == 'A+'
        # GPA: Math GP=10.00, Science GP=9.00 -> avg = 9.50
        assert report['gpa'] == Decimal('9.50')
        assert report['status'] == 'PASSED'

    def test_report_card_fails_if_any_subject_below_passing_marks(self, db_setup):
        acad_year = db_setup['acad_year']
        gs = db_setup['grading_system']
        student_1 = db_setup['student_1']
        assign_10a_math = db_setup['assign_10a_math']

        exam = Exam.objects.create(
            name='Midterm Exam 2026',
            academic_year=acad_year,
            grading_system=gs,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 10),
            is_published=True
        )
        sched = ExamSubjectSchedule.objects.create(
            exam=exam,
            subject_assignment=assign_10a_math,
            exam_date=date(2026, 10, 2),
            max_marks=Decimal('100.00'),
            passing_marks=Decimal('40.00')
        )

        # Score 35 is below passing mark 40
        StudentMark.objects.create(exam_schedule=sched, student=student_1, marks_obtained=Decimal('35.00'))

        report = generate_student_report_card(student_1, exam)
        assert report['status'] == 'FAILED'
        assert report['subject_results'][0]['is_passed'] is False
        assert report['subject_results'][0]['grade_letter'] == 'F'

    def test_marks_validation_exceeding_max_marks_raises_error(self, db_setup):
        acad_year = db_setup['acad_year']
        gs = db_setup['grading_system']
        student_1 = db_setup['student_1']
        assign_10a_math = db_setup['assign_10a_math']
        teacher_1 = db_setup['teacher_1']

        exam = Exam.objects.create(
            name='Test Exam',
            academic_year=acad_year,
            grading_system=gs,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 10)
        )
        sched = ExamSubjectSchedule.objects.create(
            exam=exam,
            subject_assignment=assign_10a_math,
            exam_date=date(2026, 10, 2),
            max_marks=Decimal('100.00')
        )

        # Attempting to record 105 marks when max is 100 must raise ValidationError
        with pytest.raises(ValidationError) as exc:
            bulk_save_subject_marks(
                exam_schedule=sched,
                marks_data=[{'student': student_1, 'marks_obtained': Decimal('105.00')}],
                teacher_profile=teacher_1
            )
        assert "cannot exceed maximum marks" in str(exc.value)
