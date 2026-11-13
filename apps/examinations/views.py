from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from apps.core.permissions import TeacherRequiredMixin, GuardianStudentAccessMixin, AdminRequiredMixin
from apps.core.models import StudentProfile
from .models import Exam, ExamSubjectSchedule, StudentMark
from .services import generate_student_report_card, bulk_save_subject_marks


class TeacherMarksEntryView(TeacherRequiredMixin, View):
    """
    Teacher marks recording sheet for an exam schedule.
    Enforces teacher authorization and input validation.
    """
    template_name = 'teacher_portal/marks_entry.html'

    def get(self, request, schedule_id):
        schedule = get_object_or_404(
            ExamSubjectSchedule.objects.select_related(
                'exam', 'subject_assignment__class_section', 'subject_assignment__subject', 'subject_assignment__teacher__user'
            ),
            id=schedule_id
        )

        user = request.user
        if not (user.is_superuser or user.is_admin):
            teacher = getattr(user, 'teacher_profile', None)
            if not teacher or schedule.subject_assignment.teacher_id != teacher.id:
                raise PermissionDenied("You are not assigned to enter marks for this subject.")

        section = schedule.subject_assignment.class_section
        enrollments = section.enrollments.filter(is_active=True).select_related('student').order_by('roll_number')

        existing_marks_map = {m.student_id: m for m in schedule.marks.all()}

        roster = []
        for enr in enrollments:
            mark = existing_marks_map.get(enr.student.id)
            roster.append({
                'enrollment': enr,
                'student': enr.student,
                'marks_obtained': mark.marks_obtained if mark else '',
                'is_absent': mark.is_absent if mark else False,
                'remarks': mark.remarks if mark else ''
            })

        return render(request, self.template_name, {
            'schedule': schedule,
            'roster': roster,
        })

    def post(self, request, schedule_id):
        schedule = get_object_or_404(ExamSubjectSchedule, id=schedule_id)
        teacher = getattr(request.user, 'teacher_profile', None)
        section = schedule.subject_assignment.class_section
        enrollments = section.enrollments.filter(is_active=True).select_related('student')

        marks_data = []
        for enr in enrollments:
            st_id = str(enr.student.id)
            is_absent = request.POST.get(f'absent_{st_id}') == 'on'
            raw_marks = request.POST.get(f'marks_{st_id}', '').strip()
            remarks = request.POST.get(f'remarks_{st_id}', '').strip()

            obt = Decimal(raw_marks) if (raw_marks and not is_absent) else Decimal('0.00')

            marks_data.append({
                'student': enr.student,
                'marks_obtained': obt,
                'is_absent': is_absent,
                'remarks': remarks
            })

        try:
            bulk_save_subject_marks(
                exam_schedule=schedule,
                marks_data=marks_data,
                teacher_profile=teacher,
                request=request
            )
            messages.success(request, f"Marks for {schedule.subject_assignment.subject.name} recorded successfully!")
            return redirect(request.path)
        except (ValidationError, PermissionDenied) as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))
            return redirect(request.path)


class GuardianStudentReportCardView(GuardianStudentAccessMixin, View):
    """
    Acceptance Criteria 3 & 4:
    Renders the calculated report card for a linked ward.
    """
    template_name = 'guardian_portal/ward_report_card.html'

    def get(self, request, student_id):
        self.check_ward_access(student_id)
        student = get_object_or_404(StudentProfile, id=student_id)

        # Available exams
        user = request.user
        if user.is_superuser or user.is_admin:
            exams = Exam.objects.all().order_by('-start_date')
        else:
            exams = Exam.objects.filter(is_published=True).order_by('-start_date')

        selected_exam_id = request.GET.get('exam_id')
        selected_exam = None
        report = None

        if selected_exam_id:
            selected_exam = exams.filter(id=selected_exam_id).first()
        elif exams.exists():
            selected_exam = exams.first()

        if selected_exam:
            report = generate_student_report_card(student, selected_exam)

        return render(request, self.template_name, {
            'student': student,
            'exams': exams,
            'selected_exam': selected_exam,
            'report': report,
        })
