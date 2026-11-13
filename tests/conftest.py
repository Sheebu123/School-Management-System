import pytest
from datetime import date
from decimal import Decimal
from apps.core.models import User, UserRole, TeacherProfile, GuardianProfile, StudentProfile
from apps.academics.models import AcademicYear, ClassLevel, ClassSection, Subject, SubjectAssignment, StudentEnrollment
from apps.examinations.models import GradingSystem, GradeRule, Exam, ExamSubjectSchedule
from apps.finance.models import FeeCategory, FeeStructure, FeeInvoice, InvoiceItem


@pytest.fixture
def db_setup(db):
    """
    Standard test fixture populating base academic, role, grading, and fee infrastructure.
    """
    # 1. Admin
    admin_user = User.objects.create_superuser(
        username='admin_test',
        email='admin@algions.test',
        password='AdminPassword123!',
        role=UserRole.ADMIN
    )

    # 2. Academic Year & Classes
    acad_year = AcademicYear.objects.create(
        name='2026-2027',
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True
    )

    class_10 = ClassLevel.objects.create(name='Grade 10', order=10)

    # 3. Teachers
    teacher_user_1 = User.objects.create_user(
        username='teacher_john',
        email='john@algions.test',
        password='TeacherPassword123!',
        role=UserRole.TEACHER,
        first_name='John',
        last_name='Doe'
    )
    teacher_1 = TeacherProfile.objects.create(
        user=teacher_user_1,
        employee_id='TCH-001',
        specialization='Mathematics'
    )

    teacher_user_2 = User.objects.create_user(
        username='teacher_sarah',
        email='sarah@algions.test',
        password='TeacherPassword123!',
        role=UserRole.TEACHER,
        first_name='Sarah',
        last_name='Connor'
    )
    teacher_2 = TeacherProfile.objects.create(
        user=teacher_user_2,
        employee_id='TCH-002',
        specialization='Physics'
    )

    # 4. Sections
    section_10a = ClassSection.objects.create(
        class_level=class_10,
        section_name='A',
        academic_year=acad_year,
        class_teacher=teacher_1
    )
    section_10b = ClassSection.objects.create(
        class_level=class_10,
        section_name='B',
        academic_year=acad_year,
        class_teacher=teacher_2
    )

    # 5. Subjects & Assignments
    math = Subject.objects.create(code='MTH101', name='Mathematics')
    science = Subject.objects.create(code='SCI101', name='Science')

    # Teacher 1 assigned to 10-A Math
    assign_10a_math = SubjectAssignment.objects.create(
        class_section=section_10a,
        subject=math,
        teacher=teacher_1
    )
    # Teacher 2 assigned to 10-B Science
    assign_10b_sci = SubjectAssignment.objects.create(
        class_section=section_10b,
        subject=science,
        teacher=teacher_2
    )

    # 6. Guardians & Students
    # Guardian 1 & Student 1 (in 10-A)
    guardian_user_1 = User.objects.create_user(
        username='guardian_alice',
        email='alice@algions.test',
        password='GuardianPassword123!',
        role=UserRole.GUARDIAN,
        first_name='Alice',
        last_name='Smith'
    )
    guardian_1 = GuardianProfile.objects.create(
        user=guardian_user_1,
        relationship='Mother'
    )
    student_1 = StudentProfile.objects.create(
        admission_number='STU-1001',
        first_name='Bobby',
        last_name='Smith',
        date_of_birth=date(2011, 5, 12),
        gender=StudentProfile.Gender.MALE,
        guardian=guardian_1
    )
    StudentEnrollment.objects.create(
        student=student_1,
        class_section=section_10a,
        roll_number=1
    )

    # Guardian 2 & Student 2 (in 10-B)
    guardian_user_2 = User.objects.create_user(
        username='guardian_bob',
        email='bob@algions.test',
        password='GuardianPassword123!',
        role=UserRole.GUARDIAN,
        first_name='Robert',
        last_name='Brown'
    )
    guardian_2 = GuardianProfile.objects.create(
        user=guardian_user_2,
        relationship='Father'
    )
    student_2 = StudentProfile.objects.create(
        admission_number='STU-1002',
        first_name='Charlie',
        last_name='Brown',
        date_of_birth=date(2011, 8, 20),
        gender=StudentProfile.Gender.MALE,
        guardian=guardian_2
    )
    StudentEnrollment.objects.create(
        student=student_2,
        class_section=section_10b,
        roll_number=1
    )

    # 7. Grading System & Standard Rules
    grading_system = GradingSystem.objects.create(name='Standard 10-Point Scale')
    GradeRule.objects.create(
        grading_system=grading_system,
        grade_letter='A+',
        grade_point=Decimal('10.00'),
        min_percentage=Decimal('90.00'),
        max_percentage=Decimal('100.00'),
        description='Outstanding'
    )
    GradeRule.objects.create(
        grading_system=grading_system,
        grade_letter='A',
        grade_point=Decimal('9.00'),
        min_percentage=Decimal('80.00'),
        max_percentage=Decimal('89.99'),
        description='Excellent'
    )
    GradeRule.objects.create(
        grading_system=grading_system,
        grade_letter='B',
        grade_point=Decimal('8.00'),
        min_percentage=Decimal('70.00'),
        max_percentage=Decimal('79.99'),
        description='Very Good'
    )
    GradeRule.objects.create(
        grading_system=grading_system,
        grade_letter='C',
        grade_point=Decimal('6.00'),
        min_percentage=Decimal('50.00'),
        max_percentage=Decimal('69.99'),
        description='Good'
    )
    GradeRule.objects.create(
        grading_system=grading_system,
        grade_letter='D',
        grade_point=Decimal('4.00'),
        min_percentage=Decimal('40.00'),
        max_percentage=Decimal('49.99'),
        description='Pass'
    )
    GradeRule.objects.create(
        grading_system=grading_system,
        grade_letter='F',
        grade_point=Decimal('0.00'),
        min_percentage=Decimal('0.00'),
        max_percentage=Decimal('39.99'),
        description='Fail'
    )

    # 8. Fee Categories & Structure
    fee_cat = FeeCategory.objects.create(name='Tuition Fee')
    fee_struct = FeeStructure.objects.create(
        academic_year=acad_year,
        class_level=class_10,
        category=fee_cat,
        amount=Decimal('1200.00'),
        due_date=date(2026, 10, 15)
    )

    return {
        'admin_user': admin_user,
        'acad_year': acad_year,
        'class_10': class_10,
        'teacher_1': teacher_1,
        'teacher_2': teacher_2,
        'section_10a': section_10a,
        'section_10b': section_10b,
        'math': math,
        'science': science,
        'assign_10a_math': assign_10a_math,
        'assign_10b_sci': assign_10b_sci,
        'guardian_1': guardian_1,
        'guardian_2': guardian_2,
        'student_1': student_1,
        'student_2': student_2,
        'grading_system': grading_system,
        'fee_cat': fee_cat,
        'fee_struct': fee_struct,
    }
