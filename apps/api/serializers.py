from rest_framework import serializers
from decimal import Decimal
from apps.core.models import User, TeacherProfile, GuardianProfile, StudentProfile, AuditLog
from apps.academics.models import AcademicYear, ClassLevel, ClassSection, Subject, SubjectAssignment, StudentEnrollment
from apps.attendance.models import AttendanceSession, AttendanceRecord, AttendanceStatus, SessionType
from apps.examinations.models import GradingSystem, GradeRule, Exam, ExamSubjectSchedule, StudentMark
from apps.finance.models import FeeCategory, FeeStructure, FeeInvoice, InvoiceItem, PaymentTransaction, PaymentMethod


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone_number']


class StudentProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    guardian_name = serializers.CharField(source='guardian.user.get_full_name', read_only=True)

    class Meta:
        model = StudentProfile
        fields = ['id', 'admission_number', 'first_name', 'last_name', 'full_name', 'date_of_birth', 'gender', 'guardian', 'guardian_name', 'is_active']


class TeacherProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = TeacherProfile
        fields = ['id', 'employee_id', 'full_name', 'email', 'specialization', 'qualification', 'is_active']


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'code', 'name', 'is_elective']


class ClassSectionSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    class_level_name = serializers.CharField(source='class_level.name', read_only=True)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    class_teacher_name = serializers.CharField(source='class_teacher.user.get_full_name', read_only=True, default=None)

    class Meta:
        model = ClassSection
        fields = ['id', 'display_name', 'class_level', 'class_level_name', 'section_name', 'academic_year', 'academic_year_name', 'class_teacher', 'class_teacher_name']


class AttendanceRecordItemSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT)
    remarks = serializers.CharField(max_length=255, required=False, allow_blank=True)


class AttendanceSubmissionSerializer(serializers.Serializer):
    class_section_id = serializers.UUIDField()
    date = serializers.DateField()
    session_type = serializers.ChoiceField(choices=SessionType.choices, default=SessionType.FULL_DAY)
    notes = serializers.CharField(required=False, allow_blank=True)
    update_existing = serializers.BooleanField(default=False)
    records = AttendanceRecordItemSerializer(many=True)


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    admission_number = serializers.CharField(source='student.admission_number', read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = ['id', 'student', 'student_name', 'admission_number', 'status', 'remarks']


class AttendanceSessionSerializer(serializers.ModelSerializer):
    class_section_name = serializers.CharField(source='class_section.display_name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.user.get_full_name', read_only=True)
    records = AttendanceRecordSerializer(many=True, read_only=True)

    class Meta:
        model = AttendanceSession
        fields = ['id', 'class_section', 'class_section_name', 'date', 'session_type', 'recorded_by_name', 'recorded_at', 'notes', 'records']


class ExamSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    grading_system_name = serializers.CharField(source='grading_system.name', read_only=True)

    class Meta:
        model = Exam
        fields = ['id', 'name', 'academic_year', 'academic_year_name', 'grading_system', 'grading_system_name', 'start_date', 'end_date', 'is_published']


class MarkItemSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    marks_obtained = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=Decimal('0.00'))
    is_absent = serializers.BooleanField(default=False)
    remarks = serializers.CharField(max_length=200, required=False, allow_blank=True)


class MarksSubmissionSerializer(serializers.Serializer):
    exam_schedule_id = serializers.UUIDField()
    marks = MarkItemSerializer(many=True)


class PaymentSubmissionSerializer(serializers.Serializer):
    invoice_id = serializers.UUIDField()
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, default=PaymentMethod.SIMULATED_CARD)
    payer_name = serializers.CharField(max_length=150)
    notes = serializers.CharField(required=False, allow_blank=True)


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = ['id', 'transaction_reference', 'amount_paid', 'payment_method', 'payment_date', 'payer_name', 'status', 'notes']


class FeeInvoiceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    admission_number = serializers.CharField(source='student.admission_number', read_only=True)
    outstanding_balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    payments = PaymentTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = FeeInvoice
        fields = ['id', 'invoice_number', 'student', 'student_name', 'admission_number', 'academic_year', 'total_amount', 'paid_amount', 'outstanding_balance', 'due_date', 'status', 'payments', 'created_at']
