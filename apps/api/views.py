from rest_framework import viewsets, views, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError, PermissionDenied
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.core.models import UserRole, StudentProfile, TeacherProfile
from apps.core.permissions import IsAdminRole, IsTeacherRole, IsGuardianRole
from apps.academics.models import ClassSection, SubjectAssignment, StudentEnrollment
from apps.attendance.models import AttendanceSession
from apps.attendance.services import record_attendance_session, get_student_attendance_summary
from apps.examinations.models import Exam, ExamSubjectSchedule
from apps.examinations.services import generate_student_report_card, bulk_save_subject_marks
from apps.finance.models import FeeInvoice
from apps.finance.services import process_fee_payment, get_financial_reconciliation_summary
from .serializers import (
    StudentProfileSerializer,
    ClassSectionSerializer,
    AttendanceSessionSerializer,
    AttendanceSubmissionSerializer,
    ExamSerializer,
    MarksSubmissionSerializer,
    FeeInvoiceSerializer,
    PaymentSubmissionSerializer,
    PaymentTransactionSerializer,
)


class ClassSectionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve class sections.
    Scoped by role: Teachers see only assigned sections; Guardians see wards' sections; Admins see all.
    """
    serializer_class = ClassSectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return ClassSection.objects.all().select_related('class_level', 'academic_year', 'class_teacher__user')
        if user.is_teacher and hasattr(user, 'teacher_profile'):
            teacher = user.teacher_profile
            # Mentored sections or subject assignments
            assigned_section_ids = SubjectAssignment.objects.filter(teacher=teacher).values_list('class_section_id', flat=True)
            return ClassSection.objects.filter(
                id__in=list(assigned_section_ids) + list(ClassSection.objects.filter(class_teacher=teacher).values_list('id', flat=True))
            ).distinct().select_related('class_level', 'academic_year', 'class_teacher__user')
        if user.is_guardian and hasattr(user, 'guardian_profile'):
            ward_ids = user.guardian_profile.students.values_list('id', flat=True)
            section_ids = StudentEnrollment.objects.filter(student_id__in=ward_ids, is_active=True).values_list('class_section_id', flat=True)
            return ClassSection.objects.filter(id__in=section_ids).distinct().select_related('class_level', 'academic_year', 'class_teacher__user')
        return ClassSection.objects.none()


class StudentProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve student profiles.
    Guardians can ONLY view their linked wards (Acceptance Criteria 4).
    """
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return StudentProfile.objects.all().select_related('guardian__user')
        if user.is_guardian and hasattr(user, 'guardian_profile'):
            return StudentProfile.objects.filter(guardian=user.guardian_profile).select_related('guardian__user')
        if user.is_teacher and hasattr(user, 'teacher_profile'):
            teacher = user.teacher_profile
            # Students in teacher's assigned classes
            assigned_section_ids = SubjectAssignment.objects.filter(teacher=teacher).values_list('class_section_id', flat=True)
            mentored_ids = ClassSection.objects.filter(class_teacher=teacher).values_list('id', flat=True)
            all_sec_ids = set(assigned_section_ids).union(set(mentored_ids))
            student_ids = StudentEnrollment.objects.filter(class_section_id__in=all_sec_ids, is_active=True).values_list('student_id', flat=True)
            return StudentProfile.objects.filter(id__in=student_ids).select_related('guardian__user')
        return StudentProfile.objects.none()

    @extend_schema(summary="Get student attendance summary metrics")
    @action(detail=True, methods=['get'])
    def attendance_summary(self, request, pk=None):
        student = self.get_object()
        summary = get_student_attendance_summary(student)
        return Response(summary)


class AttendanceSessionViewSet(viewsets.ModelViewSet):
    """
    Attendance recording and viewing endpoint.
    Acceptance Criteria 1 & 2: Safe session recording with duplicate prevention and teacher class validation.
    """
    serializer_class = AttendanceSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return AttendanceSession.objects.all().select_related('class_section', 'recorded_by__user').prefetch_related('records__student')
        if user.is_teacher and hasattr(user, 'teacher_profile'):
            teacher = user.teacher_profile
            return AttendanceSession.objects.filter(
                class_section__subject_assignments__teacher=teacher
            ).distinct().select_related('class_section', 'recorded_by__user').prefetch_related('records__student')
        return AttendanceSession.objects.none()

    @extend_schema(
        request=AttendanceSubmissionSerializer,
        responses={201: AttendanceSessionSerializer},
        summary="Submit attendance sheet for a class section"
    )
    @action(detail=False, methods=['post'], permission_classes=[IsTeacherRole | IsAdminRole])
    def record(self, request):
        serializer = AttendanceSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        class_section = get_object_or_404(ClassSection, id=data['class_section_id'])
        teacher_profile = getattr(request.user, 'teacher_profile', None)

        # Prepare records
        records_data = []
        for r in data['records']:
            student = get_object_or_404(StudentProfile, id=r['student_id'])
            records_data.append({
                'student': student,
                'status': r['status'],
                'remarks': r.get('remarks', '')
            })

        try:
            session = record_attendance_session(
                class_section=class_section,
                date=data['date'],
                recorded_by=teacher_profile,
                records_data=records_data,
                session_type=data.get('session_type', 'FULL_DAY'),
                notes=data.get('notes', ''),
                update_existing=data.get('update_existing', False),
                request=request
            )
            return Response(AttendanceSessionSerializer(session).data, status=status.HTTP_201_CREATED)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ExamViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List examinations. Guardians only see published exams.
    """
    serializer_class = ExamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_teacher or user.is_superuser:
            return Exam.objects.all().select_related('academic_year', 'grading_system')
        return Exam.objects.filter(is_published=True).select_related('academic_year', 'grading_system')


class MarksSubmissionAPIView(views.APIView):
    """
    Enter or update examination subject marks.
    Enforces teacher assignment and numerical constraints.
    """
    permission_classes = [IsTeacherRole | IsAdminRole]

    @extend_schema(request=MarksSubmissionSerializer, responses={200: dict})
    def post(self, request):
        serializer = MarksSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        sched = get_object_or_404(ExamSubjectSchedule, id=data['exam_schedule_id'])
        teacher_profile = getattr(request.user, 'teacher_profile', None)

        marks_data = []
        for item in data['marks']:
            student = get_object_or_404(StudentProfile, id=item['student_id'])
            marks_data.append({
                'student': student,
                'marks_obtained': item.get('marks_obtained', 0),
                'is_absent': item.get('is_absent', False),
                'remarks': item.get('remarks', '')
            })

        try:
            bulk_save_subject_marks(
                exam_schedule=sched,
                marks_data=marks_data,
                teacher_profile=teacher_profile,
                request=request
            )
            return Response({'message': 'Marks recorded successfully.'}, status=status.HTTP_200_OK)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StudentReportCardAPIView(views.APIView):
    """
    Generate computed student report card with automatic grade rules evaluation (Acceptance Criteria 3).
    Guarded against IDOR (Acceptance Criteria 4).
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter('exam_id', OpenApiTypes.UUID, OpenApiParameter.QUERY, required=True, description="UUID of Exam")
        ],
        responses={200: dict}
    )
    def get(self, request, student_id):
        student = get_object_or_404(StudentProfile, id=student_id)
        user = request.user

        # IDOR check for guardians
        if user.is_guardian and hasattr(user, 'guardian_profile'):
            if student.guardian_id != user.guardian_profile.id:
                raise PermissionDenied("You do not have permission to view data for this student.")

        exam_id = request.query_params.get('exam_id')
        if not exam_id:
            return Response({'detail': 'exam_id query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        exam = get_object_or_404(Exam, id=exam_id)
        if user.is_guardian and not exam.is_published:
            return Response({'detail': 'Results for this examination have not yet been published.'}, status=status.HTTP_403_FORBIDDEN)

        report = generate_student_report_card(student, exam)
        # Format response data
        return Response({
            'student_name': student.full_name,
            'admission_number': student.admission_number,
            'exam_name': exam.name,
            'total_obtained': float(report['total_obtained']),
            'total_max': float(report['total_max']),
            'aggregate_percentage': float(report['aggregate_percentage']),
            'overall_grade': report['overall_grade'],
            'gpa': float(report['gpa']),
            'status': report['status'],
            'has_marks': report['has_marks'],
            'subject_results': [
                {
                    'subject_name': s['subject_name'],
                    'subject_code': s['subject_code'],
                    'max_marks': float(s['max_marks']),
                    'passing_marks': float(s['passing_marks']),
                    'marks_obtained': float(s['marks_obtained']),
                    'percentage': float(s['percentage']),
                    'grade_letter': s['grade_letter'],
                    'grade_point': float(s['grade_point']),
                    'is_passed': s['is_passed'],
                    'is_absent': s['is_absent'],
                } for s in report['subject_results']
            ]
        })


class FeeInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve student invoices.
    Guardians are strictly restricted to their own wards (Acceptance Criteria 4).
    """
    serializer_class = FeeInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return FeeInvoice.objects.all().select_related('student__guardian__user', 'academic_year').prefetch_related('payments')
        if user.is_guardian and hasattr(user, 'guardian_profile'):
            ward_ids = user.guardian_profile.students.values_list('id', flat=True)
            return FeeInvoice.objects.filter(student_id__in=ward_ids).select_related('student__guardian__user', 'academic_year').prefetch_related('payments')
        return FeeInvoice.objects.none()


class ProcessPaymentAPIView(views.APIView):
    """
    Execute simulated fee payment with atomic reconciliation (Acceptance Criteria 5).
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=PaymentSubmissionSerializer, responses={201: PaymentTransactionSerializer})
    def post(self, request):
        serializer = PaymentSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        invoice = get_object_or_404(FeeInvoice, id=data['invoice_id'])

        # IDOR check: Guardians can only pay for their own wards
        if request.user.is_guardian and hasattr(request.user, 'guardian_profile'):
            if invoice.student.guardian_id != request.user.guardian_profile.id:
                raise PermissionDenied("You cannot pay invoices for students not linked to your guardian profile.")

        try:
            payment = process_fee_payment(
                invoice_id=invoice.id,
                amount_paid=data['amount_paid'],
                payment_method=data['payment_method'],
                payer_name=data['payer_name'],
                notes=data.get('notes', ''),
                actor=request.user,
                request=request
            )
            return Response(PaymentTransactionSerializer(payment).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FinancialReconciliationAPIView(views.APIView):
    """
    System-wide fee reconciliation dashboard statistics (Admin only).
    """
    permission_classes = [IsAdminRole]

    @extend_schema(responses={200: dict})
    def get(self, request):
        summary = get_financial_reconciliation_summary()
        return Response({
            'total_invoiced': float(summary['total_invoiced']),
            'total_collected': float(summary['total_collected']),
            'total_outstanding': float(summary['total_outstanding']),
            'recovery_rate': float(summary['recovery_rate']),
            'invoice_count': summary['invoice_count'],
            'paid_count': summary['paid_count'],
            'partially_paid_count': summary['partially_paid_count'],
            'unpaid_count': summary['unpaid_count']
        })
