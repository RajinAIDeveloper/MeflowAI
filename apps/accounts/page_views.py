from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from .forms import RegisterForm
from .mixins import PatientRequiredMixin, role_home_url
from .models import PatientMemory


DEFAULT_FAQS = [
    ("How does the AI triage work?",
     "Describe your symptoms and our AI assesses severity, recommends a department, and lists relevant doctors. It is not a substitute for emergency medical care."),
    ("Can I book appointments directly?",
     "Yes — find a doctor, choose a date and time slot, and confirm. You'll see it in My Appointments immediately."),
    ("Is my health data secure?",
     "All data is encrypted in transit and at rest. We never share personal health information with third parties."),
    ("How do I cancel or reschedule?",
     "Go to My Appointments, click the appointment, and choose Cancel or Reschedule. Cancellations must be at least 24 hours in advance."),
    ("What is the AI Assistant?",
     "The AI Assistant is a conversational agent that can answer health questions, help you find the right doctor, and manage bookings — all through natural language."),
]


def _safe_next(request):
    """Return a validated ?next/POST[next] target, or '' if unsafe/absent."""
    next_url = request.POST.get('next') or request.GET.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return ''


class LoginPageView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect(role_home_url(request.user))
        return render(request, 'patient/login.html')

    def post(self, request):
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect(_safe_next(request) or role_home_url(user))
        return render(request, 'patient/login.html', {
            'error': 'Invalid email or password.',
            'email': email,
        })


class RegisterPageView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect(role_home_url(request.user))
        return render(request, 'patient/register.html', {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('patient:dashboard')
        return render(request, 'patient/register.html', {'form': form})


class LogoutPageView(View):
    def post(self, request):
        logout(request)
        return redirect('accounts:login')


class DashboardPageView(PatientRequiredMixin, View):
    def get(self, request):
        from apps.appointments.models import Appointment

        now = timezone.now()
        upcoming = (
            Appointment.objects
            .filter(patient=request.user, scheduled_at__gte=now)
            .exclude(status='cancelled')
            .select_related('doctor__user', 'doctor__specialty')
            .order_by('scheduled_at')[:5]
        )

        quick_actions = [
            {'icon': 'emergency',      'label': 'Symptom Triage',  'sublabel': 'AI-powered assessment', 'url': '/triage/',         'bg': '#ffdad6', 'color': '#ba1a1a'},
            {'icon': 'smart_toy',      'label': 'AI Assistant',    'sublabel': 'Chat with MediFlow AI', 'url': '/assistant/',      'bg': '#d6e4ff', 'color': '#003c90'},
            {'icon': 'search',         'label': 'Find a Doctor',   'sublabel': 'Browse specialists',    'url': '/doctors/',        'bg': '#d0f0ed', 'color': '#006a61'},
            {'icon': 'calendar_month', 'label': 'Appointments',    'sublabel': 'Manage bookings',       'url': '/appointments/',   'bg': '#e0dfff', 'color': '#2724b8'},
        ]

        return render(request, 'patient/dashboard.html', {
            'upcoming_appointments': upcoming,
            'quick_actions': quick_actions,
            'hour': timezone.localtime(now).hour,
            'recent_activity': [],
        })


class AiAssistantPageView(PatientRequiredMixin, View):
    def get(self, request):
        return render(request, 'patient/ai_assistant.html')


class FindDoctorPageView(PatientRequiredMixin, View):
    def get(self, request):
        from apps.doctors.models import Doctor, Specialty
        from django.core.paginator import Paginator

        qs = Doctor.objects.select_related('user', 'specialty')

        search    = request.GET.get('search', '').strip()
        specialty = request.GET.get('specialty', '').strip()
        available = request.GET.get('available', '').strip()

        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(specialty__name__icontains=search) |
                Q(hospital__icontains=search)
            )
        if specialty:
            qs = qs.filter(specialty__name__icontains=specialty)
        if available == 'true':
            qs = qs.filter(is_available=True)

        paginator = Paginator(qs, 9)
        page_obj  = paginator.get_page(request.GET.get('page'))

        return render(request, 'patient/find_doctor.html', {
            'doctors':      page_obj,
            'specialties':  Specialty.objects.all().order_by('name'),
            'paginator':    paginator,
            'page_obj':     page_obj,
            'is_paginated': paginator.num_pages > 1,
        })


class DoctorDetailPageView(PatientRequiredMixin, View):
    def get(self, request, pk):
        from django.shortcuts import get_object_or_404
        from apps.doctors.models import Doctor

        doctor = get_object_or_404(Doctor.objects.select_related('user', 'specialty'), pk=pk)
        slots  = doctor.availability_slots.filter(is_active=True).order_by('day_of_week', 'start_time')
        return render(request, 'patient/doctor_detail.html', {'doctor': doctor, 'slots': slots})


class BookAppointmentPageView(PatientRequiredMixin, View):
    def get(self, request, pk):
        from django.shortcuts import get_object_or_404
        from apps.doctors.models import Doctor

        doctor = get_object_or_404(Doctor, pk=pk, is_available=True)
        return render(request, 'patient/book_appointment.html', {
            'doctor':    doctor,
            'today_str': timezone.localdate().isoformat(),
        })


class AppointmentsPageView(PatientRequiredMixin, View):
    def get(self, request):
        from apps.appointments.models import Appointment

        tab = request.GET.get('tab', 'upcoming')
        now = timezone.now()

        if tab == 'past':
            qs = (Appointment.objects
                  .filter(patient=request.user, scheduled_at__lt=now)
                  .select_related('doctor__user', 'doctor__specialty')
                  .order_by('-scheduled_at'))
        else:
            qs = (Appointment.objects
                  .filter(patient=request.user, scheduled_at__gte=now)
                  .exclude(status='cancelled')
                  .select_related('doctor__user', 'doctor__specialty')
                  .order_by('scheduled_at'))

        return render(request, 'patient/appointments.html', {'appointments': qs, 'tab': tab})


class AppointmentDetailPageView(PatientRequiredMixin, View):
    def get(self, request, pk):
        from django.shortcuts import get_object_or_404
        from apps.appointments.models import Appointment

        appt = get_object_or_404(
            Appointment.objects.select_related('doctor__user', 'doctor__specialty'),
            pk=pk, patient=request.user,
        )
        return render(request, 'patient/appointment_detail.html', {
            'appointment': appt,
            'is_upcoming': appt.scheduled_at > timezone.now(),
        })


class TriagePageView(PatientRequiredMixin, View):
    def get(self, request):
        return render(request, 'patient/triage.html')


class ProfilePageView(PatientRequiredMixin, View):
    def get(self, request):
        memory, _ = PatientMemory.objects.get_or_create(patient=request.user)
        return render(request, 'patient/profile.html', {'patient_memory': memory})


class HelpPageView(PatientRequiredMixin, View):
    def get(self, request):
        return render(request, 'patient/help.html', {'default_faqs': DEFAULT_FAQS})
