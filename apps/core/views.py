from django.shortcuts import redirect, render
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import UserRole


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_superuser or user.role == UserRole.ADMIN:
            return '/admin-portal/'
        elif user.role == UserRole.TEACHER:
            return '/teacher-portal/'
        elif user.role in (UserRole.GUARDIAN, UserRole.STUDENT):
            return '/guardian-portal/'
        return '/'


class DashboardRedirectView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_superuser or user.role == UserRole.ADMIN:
            return redirect('admin-dashboard')
        elif user.role == UserRole.TEACHER:
            return redirect('teacher-dashboard')
        elif user.role in (UserRole.GUARDIAN, UserRole.STUDENT):
            return redirect('guardian-dashboard')
        return redirect('login')


def custom_logout_view(request):
    logout(request)
    return redirect('login')
