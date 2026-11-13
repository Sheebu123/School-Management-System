from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import User, UserRole, TeacherProfile, GuardianProfile, StudentProfile
from apps.academics.models import AcademicYear, ClassLevel, ClassSection, Subject, SubjectAssignment, StudentEnrollment
from apps.attendance.models import AttendanceSession, AttendanceRecord, AttendanceStatus, SessionType
from apps.examinations.models import GradingSystem, GradeRule, Exam, ExamSubjectSchedule, StudentMark
from apps.finance.models import FeeCategory, FeeStructure, FeeInvoice, InvoiceItem, PaymentTransaction, InvoiceStatus, PaymentMethod
from apps.core.services import log_audit_event


class Command(BaseCommand):
    help = "Seeds synthetic demo data for ALGIONS School Management System evaluation."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding synthetic demo data..."))

        # 1. Administrator User
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@algions.edu',
                'first_name': 'Sheebu',
                'last_name': 'Tiwari',
                'role': UserRole.ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('AdminPass123!')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created Admin: admin / AdminPass123!"))

        # 2. Teachers
        teacher_user_1, created = User.objects.get_or_create(
            username='teacher.john',
            defaults={
                'email': 'john.doe@algions.edu',
                'first_name': 'John',
                'last_name': 'Doe',
                'role': UserRole.TEACHER,
                'phone_number': '+1-555-0101',
            }
        )
        if created:
            teacher_user_1.set_password('TeacherPass123!')
            teacher_user_1.save()
        teacher_1, _ = TeacherProfile.objects.get_or_create(
            user=teacher_user_1,
            defaults={
                'employee_id': 'TCH-1001',
                'specialization': 'Mathematics & Analytical Geometry',
                'qualification': 'M.Sc. Mathematics, B.Ed.',
            }
        )

        teacher_user_2, created = User.objects.get_or_create(
            username='teacher.sarah',
            defaults={
                'email': 'sarah.connor@algions.edu',
                'first_name': 'Sarah',
                'last_name': 'Connor',
                'role': UserRole.TEACHER,
                'phone_number': '+1-555-0102',
            }
        )
        if created:
            teacher_user_2.set_password('TeacherPass123!')
            teacher_user_2.save()
        teacher_2, _ = TeacherProfile.objects.get_or_create(
            user=teacher_user_2,
            defaults={
                'employee_id': 'TCH-1002',
                'specialization': 'Physics & Computational Sciences',
                'qualification': 'M.Sc. Applied Physics',
            }
        )

        # 3. Guardians
        guardian_user_1, created = User.objects.get_or_create(
            username='guardian.alice',
            defaults={
                'email': 'alice.smith@example.com',
                'first_name': 'Alice',
                'last_name': 'Smith',
                'role': UserRole.GUARDIAN,
                'phone_number': '+1-555-0201',
            }
        )
        if created:
            guardian_user_1.set_password('GuardianPass123!')
            guardian_user_1.save()
        guardian_1, _ = GuardianProfile.objects.get_or_create(
            user=guardian_user_1,
            defaults={
                'relationship': 'Mother',
                'occupation': 'Software Architect',
                'emergency_contact': '+1-555-0201',
                'address': '742 Evergreen Terrace, Springfield',
            }
        )

        guardian_user_2, created = User.objects.get_or_create(
            username='guardian.bob',
            defaults={
                'email': 'bob.brown@example.com',
                'first_name': 'Robert',
                'last_name': 'Brown',
                'role': UserRole.GUARDIAN,
                'phone_number': '+1-555-0202',
            }
        )
        if created:
            guardian_user_2.set_password('GuardianPass123!')
            guardian_user_2.save()
        guardian_2, _ = GuardianProfile.objects.get_or_create(
            user=guardian_user_2,
            defaults={
                'relationship': 'Father',
                'occupation': 'Civil Engineer',
                'emergency_contact': '+1-555-0202',
                'address': '124 Conch Street, Springfield',
            }
        )

        # 4. Academic Infrastructure
        acad_year, _ = AcademicYear.objects.get_or_create(
            name='2026-2027',
            defaults={
                'start_date': date(2026, 4, 1),
                'end_date': date(2027, 3, 31),
                'is_current': True,
            }
        )
        acad_year.is_current = True
        acad_year.save()

        grade_10, _ = ClassLevel.objects.get_or_create(name='Grade 10', defaults={'order': 10})
        grade_9, _ = ClassLevel.objects.get_or_create(name='Grade 9', defaults={'order': 9})

        # Class Sections
        section_10a, _ = ClassSection.objects.get_or_create(
            class_level=grade_10,
            section_name='A',
            academic_year=acad_year,
            defaults={'class_teacher': teacher_1}
        )
        section_10b, _ = ClassSection.objects.get_or_create(
            class_level=grade_10,
            section_name='B',
            academic_year=acad_year,
            defaults={'class_teacher': teacher_2}
        )

        # Subjects
        math, _ = Subject.objects.get_or_create(code='MTH101', defaults={'name': 'Advanced Mathematics'})
        physics, _ = Subject.objects.get_or_create(code='PHY101', defaults={'name': 'Physics & Mechanics'})
        english, _ = Subject.objects.get_or_create(code='ENG101', defaults={'name': 'English Literature'})
        comp_sci, _ = Subject.objects.get_or_create(code='CS101', defaults={'name': 'Computer Science'})

        # Assignments
        # Teacher 1 -> 10-A Math
        SubjectAssignment.objects.get_or_create(
            class_section=section_10a,
            subject=math,
            defaults={'teacher': teacher_1}
        )
        # Teacher 2 -> 10-A Physics
        SubjectAssignment.objects.get_or_create(
            class_section=section_10a,
            subject=physics,
            defaults={'teacher': teacher_2}
        )
        # Teacher 2 -> 10-B Physics
        SubjectAssignment.objects.get_or_create(
            class_section=section_10b,
            subject=physics,
            defaults={'teacher': teacher_2}
        )

        # 5. Students & Enrollments
        # Student 1: Bobby Smith (Ward of Alice Smith) in Grade 10-A
        student_1, _ = StudentProfile.objects.get_or_create(
            admission_number='ADM-2026-001',
            defaults={
                'first_name': 'Bobby',
                'last_name': 'Smith',
                'date_of_birth': date(2011, 4, 15),
                'gender': StudentProfile.Gender.MALE,
                'guardian': guardian_1,
                'is_active': True,
            }
        )
        StudentEnrollment.objects.get_or_create(
            student=student_1,
            class_section=section_10a,
            defaults={'roll_number': 1}
        )

        # Student 2: Emily Smith (Sister of Bobby, Ward of Alice Smith) in Grade 10-A
        student_2, _ = StudentProfile.objects.get_or_create(
            admission_number='ADM-2026-002',
            defaults={
                'first_name': 'Emily',
                'last_name': 'Smith',
                'date_of_birth': date(2011, 9, 28),
                'gender': StudentProfile.Gender.FEMALE,
                'guardian': guardian_1,
                'is_active': True,
            }
        )
        StudentEnrollment.objects.get_or_create(
            student=student_2,
            class_section=section_10a,
            defaults={'roll_number': 2}
        )

        # Student 3: Charlie Brown (Ward of Robert Brown) in Grade 10-B
        student_3, _ = StudentProfile.objects.get_or_create(
            admission_number='ADM-2026-003',
            defaults={
                'first_name': 'Charlie',
                'last_name': 'Brown',
                'date_of_birth': date(2011, 11, 5),
                'gender': StudentProfile.Gender.MALE,
                'guardian': guardian_2,
                'is_active': True,
            }
        )
        StudentEnrollment.objects.get_or_create(
            student=student_3,
            class_section=section_10b,
            defaults={'roll_number': 1}
        )

        # 6. Grading System & Standard Rules
        grading_sys, _ = GradingSystem.objects.get_or_create(name='ALGIONS 10-Point Scale')
        rules = [
            ('A+', Decimal('10.00'), Decimal('90.00'), Decimal('100.00'), 'Outstanding Performance'),
            ('A', Decimal('9.00'), Decimal('80.00'), Decimal('89.99'), 'Excellent Performance'),
            ('B', Decimal('8.00'), Decimal('70.00'), Decimal('79.99'), 'Very Good Performance'),
            ('C', Decimal('6.00'), Decimal('50.00'), Decimal('69.99'), 'Good / Above Average'),
            ('D', Decimal('4.00'), Decimal('40.00'), Decimal('49.99'), 'Pass Standard'),
            ('F', Decimal('0.00'), Decimal('0.00'), Decimal('39.99'), 'Needs Improvement / Fail'),
        ]
        for gl, gp, min_p, max_p, desc in rules:
            GradeRule.objects.get_or_create(
                grading_system=grading_sys,
                grade_letter=gl,
                defaults={
                    'grade_point': gp,
                    'min_percentage': min_p,
                    'max_percentage': max_p,
                    'description': desc
                }
            )

        # 7. Examination, Schedules & Marks
        midterm_exam, _ = Exam.objects.get_or_create(
            name='Term 1 Midterm Examination 2026',
            academic_year=acad_year,
            defaults={
                'grading_system': grading_sys,
                'start_date': date(2026, 10, 5),
                'end_date': date(2026, 10, 15),
                'is_published': True
            }
        )

        # Schedule 1: 10-A Math
        assign_10a_math = SubjectAssignment.objects.get(class_section=section_10a, subject=math)
        sched_math, _ = ExamSubjectSchedule.objects.get_or_create(
            exam=midterm_exam,
            subject_assignment=assign_10a_math,
            defaults={
                'exam_date': date(2026, 10, 6),
                'max_marks': Decimal('100.00'),
                'passing_marks': Decimal('40.00')
            }
        )
        # Schedule 2: 10-A Physics
        assign_10a_phy = SubjectAssignment.objects.get(class_section=section_10a, subject=physics)
        sched_phy, _ = ExamSubjectSchedule.objects.get_or_create(
            exam=midterm_exam,
            subject_assignment=assign_10a_phy,
            defaults={
                'exam_date': date(2026, 10, 8),
                'max_marks': Decimal('100.00'),
                'passing_marks': Decimal('40.00')
            }
        )

        # Marks for Student 1 (Bobby): Math 94.00 (A+), Physics 88.50 (A)
        StudentMark.objects.get_or_create(
            exam_schedule=sched_math,
            student=student_1,
            defaults={'marks_obtained': Decimal('94.00'), 'remarks': 'Excellent analytical solving'}
        )
        StudentMark.objects.get_or_create(
            exam_schedule=sched_phy,
            student=student_1,
            defaults={'marks_obtained': Decimal('88.50'), 'remarks': 'Strong conceptual grasp'}
        )

        # Marks for Student 2 (Emily): Math 78.00 (B), Physics 82.00 (A)
        StudentMark.objects.get_or_create(
            exam_schedule=sched_math,
            student=student_2,
            defaults={'marks_obtained': Decimal('78.00'), 'remarks': 'Good effort'}
        )
        StudentMark.objects.get_or_create(
            exam_schedule=sched_phy,
            student=student_2,
            defaults={'marks_obtained': Decimal('82.00'), 'remarks': 'Consistently high performance'}
        )

        # 8. Past Attendance Sessions & Records
        for day_offset in range(1, 6):
            att_date = date.today() - timedelta(days=day_offset)
            session, _ = AttendanceSession.objects.get_or_create(
                class_section=section_10a,
                date=att_date,
                session_type=SessionType.FULL_DAY,
                defaults={
                    'recorded_by': teacher_1,
                    'notes': f'Standard academic session on {att_date}'
                }
            )
            # Student 1: Present
            AttendanceRecord.objects.get_or_create(
                session=session,
                student=student_1,
                defaults={'status': AttendanceStatus.PRESENT}
            )
            # Student 2: Present on most, 1 excused
            st2_status = AttendanceStatus.EXCUSED if day_offset == 3 else AttendanceStatus.PRESENT
            AttendanceRecord.objects.get_or_create(
                session=session,
                student=student_2,
                defaults={'status': st2_status, 'remarks': 'Medical appointment' if day_offset == 3 else ''}
            )

        # 9. Fee Structures & Invoices
        tuition_cat, _ = FeeCategory.objects.get_or_create(name='Tuition Fee', defaults={'description': 'Core academic instruction'})
        lab_cat, _ = FeeCategory.objects.get_or_create(name='Science & Robotics Lab', defaults={'description': 'Practical lab apparatus'})

        FeeStructure.objects.get_or_create(
            academic_year=acad_year,
            class_level=grade_10,
            category=tuition_cat,
            defaults={'amount': Decimal('1200.00'), 'due_date': date(2026, 11, 30)}
        )
        FeeStructure.objects.get_or_create(
            academic_year=acad_year,
            class_level=grade_10,
            category=lab_cat,
            defaults={'amount': Decimal('300.00'), 'due_date': date(2026, 11, 30)}
        )

        # Invoice for Student 1 (Bobby): Total $1500, Partial Paid $500, Outstanding $1000
        inv_1, _ = FeeInvoice.objects.get_or_create(
            invoice_number='INV-2026-STU001',
            defaults={
                'student': student_1,
                'academic_year': acad_year,
                'total_amount': Decimal('1500.00'),
                'paid_amount': Decimal('500.00'),
                'due_date': date(2026, 11, 30),
                'status': InvoiceStatus.PARTIALLY_PAID
            }
        )
        if not inv_1.items.exists():
            InvoiceItem.objects.create(invoice=inv_1, fee_category=tuition_cat, description='Grade 10 Tuition Fee', amount=Decimal('1200.00'))
            InvoiceItem.objects.create(invoice=inv_1, fee_category=lab_cat, description='Science & Robotics Lab', amount=Decimal('300.00'))

        PaymentTransaction.objects.get_or_create(
            transaction_reference='TXN-DEMO-BOBBY-500',
            defaults={
                'invoice': inv_1,
                'amount_paid': Decimal('500.00'),
                'payment_method': PaymentMethod.SIMULATED_CARD,
                'payer_name': 'Alice Smith',
                'status': PaymentTransaction.TransactionStatus.SUCCESS,
                'notes': 'First installment paid via Visa card (simulated)'
            }
        )

        # Invoice for Student 2 (Emily): Total $1500, Paid $1500, Outstanding $0 (PAID)
        inv_2, _ = FeeInvoice.objects.get_or_create(
            invoice_number='INV-2026-STU002',
            defaults={
                'student': student_2,
                'academic_year': acad_year,
                'total_amount': Decimal('1500.00'),
                'paid_amount': Decimal('1500.00'),
                'due_date': date(2026, 11, 30),
                'status': InvoiceStatus.PAID
            }
        )
        if not inv_2.items.exists():
            InvoiceItem.objects.create(invoice=inv_2, fee_category=tuition_cat, description='Grade 10 Tuition Fee', amount=Decimal('1200.00'))
            InvoiceItem.objects.create(invoice=inv_2, fee_category=lab_cat, description='Science & Robotics Lab', amount=Decimal('300.00'))

        PaymentTransaction.objects.get_or_create(
            transaction_reference='TXN-DEMO-EMILY-1500',
            defaults={
                'invoice': inv_2,
                'amount_paid': Decimal('1500.00'),
                'payment_method': PaymentMethod.UPI,
                'payer_name': 'Alice Smith',
                'status': PaymentTransaction.TransactionStatus.SUCCESS,
                'notes': 'Full term payment via UPI (simulated)'
            }
        )

        # 10. Audit log entries
        log_audit_event(
            actor=admin_user,
            action='SEED_SYSTEM_DATA',
            entity_type='System',
            entity_id='INITIAL_SETUP',
            description='Initialized synthetic evaluation demo data for ALGIONS School Management System.'
        )

        self.stdout.write(self.style.SUCCESS("Synthetic demo data seeded successfully!"))
        self.stdout.write(self.style.NOTICE("""
Available Demo Accounts:
  1. Administrator: admin / AdminPass123!
  2. Teacher (Math): teacher.john / TeacherPass123!
  3. Teacher (Physics): teacher.sarah / TeacherPass123!
  4. Guardian (Wards: Bobby & Emily Smith): guardian.alice / GuardianPass123!
  5. Guardian (Ward: Charlie Brown): guardian.bob / GuardianPass123!
"""))
