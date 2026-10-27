from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import UserProfile


def role_required(*allowed_roles):
    def decorator(view_func):
        @login_required(login_url="login")
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_active:
                raise PermissionDenied("Your account is inactive.")

            # Superusers retain access even without a profile.
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            has_allowed_role = UserProfile.objects.filter(
                user=request.user,
                role__in=allowed_roles,
            ).exists()

            if not has_allowed_role:
                raise PermissionDenied(
                    "You do not have permission to access this page."
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator