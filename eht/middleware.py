from django.conf import settings
from django.shortcuts import redirect


_EXEMPT_PREFIXES = (
    '/login/',
    '/logout/',
    '/register/',
)


class LoginRequiredMiddleware:
    """Require authentication for every URL except the login page, logout, and admin."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path_info
            admin_prefix = f"/{getattr(settings, 'ADMIN_SITE_PATH', 'admin/')}"
            if not (path == '/' or path.startswith(admin_prefix) or any(path.startswith(p) for p in _EXEMPT_PREFIXES)):
                login_url = getattr(settings, 'LOGIN_URL', '/login/')
                return redirect(f'{login_url}?next={path}')
        return self.get_response(request)
