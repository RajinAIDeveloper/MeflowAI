"""Role-based access control helpers for the Django-template frontend."""
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect


def role_home_url(user):
    """Return the named URL of the landing page for a user's role."""
    if not getattr(user, 'is_authenticated', False):
        return 'accounts:login'
    role = getattr(user, 'role', None)
    if role == 'doctor':
        return 'doctor:dashboard'
    if role == 'admin':
        return 'staff:dashboard'
    return 'patient:dashboard'


class RoleRequiredMixin(AccessMixin):
    """Require login and (optionally) a specific role.

    Anonymous users are redirected to login (with ?next). Authenticated users
    with the wrong role are bounced to their own portal's home page.
    """
    required_role = None
    login_url = '/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.required_role and request.user.role != self.required_role:
            return redirect(role_home_url(request.user))
        return super().dispatch(request, *args, **kwargs)


class PatientRequiredMixin(RoleRequiredMixin):
    required_role = 'patient'


class DoctorRequiredMixin(RoleRequiredMixin):
    required_role = 'doctor'


class AdminRequiredMixin(RoleRequiredMixin):
    required_role = 'admin'
