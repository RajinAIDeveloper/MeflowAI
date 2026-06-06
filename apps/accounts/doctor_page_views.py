"""Doctor portal — server-rendered pages (session auth, role=doctor)."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.appointments.models import Appointment
from apps.doctors.models import AvailabilitySlot, Doctor, Specialty

from .mixins import DoctorRequiredMixin


def _get_profile(user):
    """Return the doctor's profile, creating a stub if one doesn't exist yet."""
    profile, _ = Doctor.objects.get_or_create(user=user, defaults={'hospital': ''})
    return profile


class DoctorDashboardView(DoctorRequiredMixin, View):
    def get(self, request):
        profile = _get_profile(request.user)
        now = timezone.now()
        today = timezone.localdate()

        base = Appointment.objects.filter(doctor=profile)
        todays = (base.filter(scheduled_at__date=today)
                      .exclude(status='cancelled')
                      .select_related('patient', 'doctor__specialty')
                      .order_by('scheduled_at'))
        upcoming = (base.filter(scheduled_at__gte=now)
                        .exclude(status='cancelled')
                        .select_related('patient')
                        .order_by('scheduled_at')[:6])

        stats = {
            'today':     todays.count(),
            'pending':   base.filter(status='pending').count(),
            'upcoming':  base.filter(scheduled_at__gte=now).exclude(status='cancelled').count(),
            'patients':  base.values('patient').distinct().count(),
        }
        return render(request, 'doctor/dashboard.html', {
            'profile': profile,
            'todays_appointments': todays,
            'upcoming_appointments': upcoming,
            'stats': stats,
        })


class DoctorAppointmentsView(DoctorRequiredMixin, View):
    def get(self, request):
        profile = _get_profile(request.user)
        tab = request.GET.get('tab', 'upcoming')
        now = timezone.now()
        qs = Appointment.objects.filter(doctor=profile).select_related('patient', 'doctor__specialty')

        if tab == 'past':
            qs = qs.filter(scheduled_at__lt=now).order_by('-scheduled_at')
        elif tab == 'pending':
            qs = qs.filter(status='pending').order_by('scheduled_at')
        else:
            tab = 'upcoming'
            qs = qs.filter(scheduled_at__gte=now).exclude(status='cancelled').order_by('scheduled_at')

        return render(request, 'doctor/appointments.html', {'appointments': qs, 'tab': tab})


class DoctorAppointmentDetailView(DoctorRequiredMixin, View):
    def _get(self, request, pk):
        profile = _get_profile(request.user)
        return get_object_or_404(
            Appointment.objects.select_related('patient', 'doctor__specialty'),
            pk=pk, doctor=profile,
        )

    def get(self, request, pk):
        appt = self._get(request, pk)
        return render(request, 'doctor/appointment_detail.html', {
            'appointment': appt,
            'is_upcoming': appt.scheduled_at > timezone.now(),
        })

    def post(self, request, pk):
        appt = self._get(request, pk)
        action = request.POST.get('action')

        if action == 'confirm' and appt.status == Appointment.Status.PENDING:
            appt.confirm()
            messages.success(request, 'Appointment confirmed.')
        elif action == 'complete' and appt.status in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED):
            appt.doctor_notes = request.POST.get('doctor_notes', appt.doctor_notes)
            appt.status = Appointment.Status.COMPLETED
            appt.save(update_fields=['status', 'doctor_notes', 'updated_at'])
            messages.success(request, 'Appointment marked complete.')
        elif action == 'cancel' and appt.status in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED):
            appt.cancel()
            messages.success(request, 'Appointment cancelled.')
        elif action == 'notes':
            appt.doctor_notes = request.POST.get('doctor_notes', '')
            appt.save(update_fields=['doctor_notes', 'updated_at'])
            messages.success(request, 'Notes saved.')
        else:
            messages.error(request, 'That action is not available for this appointment.')

        return redirect('doctor:appointment_detail', pk=pk)


class DoctorAvailabilityView(DoctorRequiredMixin, View):
    def get(self, request):
        profile = _get_profile(request.user)
        slots = profile.availability_slots.order_by('day_of_week', 'start_time')
        return render(request, 'doctor/availability.html', {
            'slots': slots,
            'days': AvailabilitySlot.Day.choices,
        })

    def post(self, request):
        profile = _get_profile(request.user)
        action = request.POST.get('action', 'add')

        if action == 'delete':
            slot_id = request.POST.get('slot_id')
            AvailabilitySlot.objects.filter(pk=slot_id, doctor=profile).delete()
            messages.success(request, 'Availability slot removed.')
            return redirect('doctor:availability')

        try:
            AvailabilitySlot.objects.create(
                doctor=profile,
                day_of_week=int(request.POST['day_of_week']),
                start_time=request.POST['start_time'],
                end_time=request.POST['end_time'],
                slot_duration_minutes=int(request.POST.get('slot_duration_minutes') or 30),
                is_active=request.POST.get('is_active') == 'on',
            )
            messages.success(request, 'Availability slot added.')
        except Exception:
            messages.error(request, 'Could not add slot — check the times (and avoid duplicates for the same day/start).')
        return redirect('doctor:availability')


class DoctorProfileView(DoctorRequiredMixin, View):
    def get(self, request):
        profile = _get_profile(request.user)
        return render(request, 'doctor/profile.html', {
            'profile': profile,
            'specialties': Specialty.objects.all(),
        })

    def post(self, request):
        profile = _get_profile(request.user)
        user = request.user

        # User basic info
        user.first_name = request.POST.get('first_name', user.first_name).strip()
        user.last_name = request.POST.get('last_name', user.last_name).strip()
        user.phone = request.POST.get('phone', user.phone).strip()
        user.save(update_fields=['first_name', 'last_name', 'phone'])

        # Doctor profile
        specialty_id = request.POST.get('specialty') or None
        profile.specialty_id = specialty_id
        profile.hospital = request.POST.get('hospital', '').strip()
        profile.location = request.POST.get('location', '').strip()
        profile.bio = request.POST.get('bio', '').strip()
        profile.languages = request.POST.get('languages', '').strip() or 'English'
        profile.is_available = request.POST.get('is_available') == 'on'
        try:
            profile.years_experience = int(request.POST.get('years_experience') or 0)
            profile.consultation_fee = request.POST.get('consultation_fee') or 0
        except (ValueError, TypeError):
            messages.error(request, 'Years of experience and fee must be numbers.')
            return redirect('doctor:profile')
        profile.save()

        messages.success(request, 'Profile updated.')
        return redirect('doctor:profile')
