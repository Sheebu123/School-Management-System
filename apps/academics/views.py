from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from apps.core.permissions import AdminRequiredMixin, TeacherRequiredMixin
from .models import ClassSection, SubjectAssignment, StudentEnrollment


class AdminClassesListView(AdminRequiredMixin, ListView):
    model = ClassSection
    template_name = 'admin_portal/academics_classes.html'
    context_object_name = 'sections'

    def get_queryset(self):
        return ClassSection.objects.select_related(
            'class_level', 'academic_year', 'class_teacher__user'
        ).prefetch_related('enrollments', 'subject_assignments__subject', 'subject_assignments__teacher__user')


class AdminClassDetailView(AdminRequiredMixin, DetailView):
    model = ClassSection
    template_name = 'admin_portal/class_detail.html'
    context_object_name = 'section'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['enrollments'] = self.object.enrollments.select_related('student__guardian__user').order_by('roll_number')
        ctx['subject_assignments'] = self.object.subject_assignments.select_related('subject', 'teacher__user')
        return ctx


class TeacherDashboardView(TeacherRequiredMixin, ListView):
    """
    Teacher Portal Workspace.
    Acceptance Criteria 1: Displays only assigned classes.
    """
    model = ClassSection
    template_name = 'teacher_portal/dashboard.html'
    context_object_name = 'sections'

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'teacher_profile'):
            return ClassSection.objects.none()
        teacher = user.teacher_profile
        assigned_sec_ids = SubjectAssignment.objects.filter(teacher=teacher).values_list('class_section_id', flat=True)
        mentored_ids = ClassSection.objects.filter(class_teacher=teacher).values_list('id', flat=True)
        all_ids = set(assigned_sec_ids).union(set(mentored_ids))
        return ClassSection.objects.filter(id__in=all_ids).select_related(
            'class_level', 'academic_year', 'class_teacher__user'
        ).prefetch_related('enrollments', 'subject_assignments__subject')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        teacher = getattr(self.request.user, 'teacher_profile', None)
        ctx['teacher'] = teacher
        if teacher:
            ctx['my_subject_assignments'] = SubjectAssignment.objects.filter(teacher=teacher).select_related(
                'class_section__class_level', 'subject'
            )
        return ctx
