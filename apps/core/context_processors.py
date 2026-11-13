def system_context(request):
    """
    Global template context variables for SMS application branding and user roles.
    """
    context = {
        'APP_NAME': 'ALGIONS School Management System',
        'APP_ORGANIZATION': 'ALGIONS AI LABS PRIVATE LIMITED',
        'CANDIDATE_NAME': 'Sheebu Tiwari',
        'REGISTRATION_NO': '12310860',
    }
    if request.user.is_authenticated:
        context['is_admin'] = request.user.is_admin
        context['is_teacher'] = request.user.is_teacher
        context['is_guardian'] = request.user.is_guardian
        context['is_student'] = request.user.is_student
        context['user_role'] = request.user.role
    return context
