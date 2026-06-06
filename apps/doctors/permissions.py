from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsDoctor(BasePermission):
    """Allows access only to users with the doctor role who have a doctor profile."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == 'doctor'
            and hasattr(request.user, 'doctor_profile')
        )


class IsDoctorOwner(BasePermission):
    """Object-level: obj must be a Doctor instance owned by the requesting user."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == 'doctor'
            and hasattr(request.user, 'doctor_profile')
        )

    def has_object_permission(self, request, view, obj):
        from .models import Doctor
        if isinstance(obj, Doctor):
            return obj == request.user.doctor_profile
        # For related objects (e.g. AvailabilitySlot), check via the doctor FK
        return getattr(obj, 'doctor_id', None) == request.user.doctor_profile.pk
