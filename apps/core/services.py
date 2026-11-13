from .models import AuditLog


def get_client_ip(request):
    """
    Safely extract client IP from incoming request headers.
    """
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_audit_event(actor=None, action="", entity_type="", entity_id="", description="", changes=None, request=None):
    """
    Persist an audit log event to record critical state changes.
    """
    ip_address = get_client_ip(request)
    if actor is None and request and hasattr(request, 'user') and request.user.is_authenticated:
        actor = request.user

    return AuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        description=description,
        changes=changes or {},
        ip_address=ip_address
    )
