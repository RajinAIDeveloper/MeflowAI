"""
LangChain tools that the booking agent can call.
Each tool is a thin wrapper over the Django ORM so no HTTP round-trips.
"""
import re
from datetime import datetime
from langchain.tools import tool


def _specialty_stem(term: str) -> str:
    """Normalize a specialty query so 'cardiologist'/'cardiology' both match
    the stored 'Cardiology' (strip common suffixes -> shared stem)."""
    return re.sub(r'(ologist|ology|iatrist|iatry|ist|ics|y)$', '', term.strip().lower())


# Common lay/synonym phrasings -> canonical specialty name (substring-matched).
SPECIALTY_ALIASES = {
    'gp': 'General Practice', 'g.p': 'General Practice',
    'family medicine': 'General Practice', 'family doctor': 'General Practice',
    'primary care': 'General Practice', 'pcp': 'General Practice',
    'general practitioner': 'General Practice', 'internal medicine': 'General Practice',
    'heart': 'Cardiology', 'cardiac': 'Cardiology',
    'skin': 'Dermatology', 'brain': 'Neurology', 'nerve': 'Neurology',
    'child': 'Pediatrics', 'kids': 'Pediatrics', 'paediatric': 'Pediatrics',
    'bone': 'Orthopedics', 'joint': 'Orthopedics', 'orthopaedic': 'Orthopedics',
}


@tool
def search_doctors(query: str, available_only: bool = True) -> list[dict]:
    """Find doctors by specialty (e.g. 'cardiology', 'GP', 'skin') OR by name
    (e.g. 'Dr Chen', 'Sarah Chen', 'Okafor'). Returns doctors with an
    `accepting_new` flag. If none are currently accepting new appointments, still
    returns the matches (accepting_new=False) so you can tell the patient they
    exist but aren't taking bookings — never claim there are simply 'no doctors'
    if some match."""
    from django.db.models import Q
    from apps.doctors.models import Doctor

    # Drop an honorific so "Dr Chen" -> "Chen".
    term = re.sub(r'^\s*(dr\.?|doctor)\s+', '', (query or '').strip(), flags=re.I).strip()
    low = term.lower()

    # Specialty match (full + stem) and doctor-name match (full).
    match = (Q(specialty__name__icontains=term) |
             Q(user__first_name__icontains=term) |
             Q(user__last_name__icontains=term))
    stem = _specialty_stem(term)
    if stem and stem != low:
        match |= Q(specialty__name__icontains=stem)
    # Synonyms / lay terms (e.g. "GP", "family medicine" -> General Practice).
    for alias, canonical in SPECIALTY_ALIASES.items():
        if alias in low:
            match |= Q(specialty__name__iexact=canonical)
    # Per-word matching so "general practitioner" -> General Practice and
    # "Sarah Chen" -> the doctor named Chen.
    for word in re.split(r'\W+', low):
        if len(word) >= 3:
            match |= (Q(specialty__name__icontains=word) |
                      Q(user__first_name__icontains=word) |
                      Q(user__last_name__icontains=word))
            wstem = _specialty_stem(word)
            if wstem and len(wstem) >= 4 and wstem != word:
                match |= Q(specialty__name__icontains=wstem)
    qs = Doctor.objects.select_related('user', 'specialty').filter(match).distinct()

    available = qs.filter(is_available=True)
    # Prefer accepting doctors; fall back to all matches so we never wrongly say
    # "no doctors" when some exist but aren't accepting new appointments.
    chosen = available if (available_only and available.exists()) else qs

    return [
        {
            'id': d.pk,
            'name': f"Dr. {d.user.get_full_name()}",
            'specialty': d.specialty.name if d.specialty else '',
            'hospital': d.hospital,
            'rating': float(d.rating),
            'consultation_fee': float(d.consultation_fee),
            'accepting_new': d.is_available,
        }
        for d in chosen[:10]
    ]


@tool
def check_schedule(doctor_id: int, date: str) -> list[str]:
    """
    Return available time slots for a doctor on a given date (YYYY-MM-DD).
    Excludes times already booked.
    """
    from datetime import date as date_cls, time, timedelta
    from apps.doctors.models import AvailabilitySlot
    from apps.appointments.models import Appointment

    try:
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        return ['Invalid date format. Use YYYY-MM-DD.']

    day_of_week = target_date.weekday()
    slots = AvailabilitySlot.objects.filter(
        doctor_id=doctor_id, day_of_week=day_of_week, is_active=True
    )

    booked_times = set(
        Appointment.objects.filter(
            doctor_id=doctor_id,
            scheduled_at__date=target_date,
            status__in=['pending', 'confirmed'],
        ).values_list('scheduled_at__time', flat=True)
    )

    available = []
    for slot in slots:
        current = datetime.combine(target_date, slot.start_time)
        end = datetime.combine(target_date, slot.end_time)
        delta = timedelta(minutes=slot.slot_duration_minutes)
        while current + delta <= end:
            if current.time() not in booked_times:
                available.append(current.strftime('%H:%M'))
            current += delta

    return available if available else ['No available slots on this day.']


def make_patient_tools(patient_id: int):
    """Build booking/cancel tools bound to the logged-in patient.

    patient_id is captured in the closure and NOT exposed in the tool schema, so
    the agent never needs to ask the user for it (they're already authenticated).
    """

    @tool
    def create_booking(
        doctor_id: int,
        scheduled_at: str,
        reason: str = '',
        appointment_type: str = 'in_person',
    ) -> dict:
        """
        Book an appointment for the current patient. `doctor_id` MUST be a real id
        from a search_doctors result (never guess it). scheduled_at must be ISO-8601
        (e.g. 2026-09-01T10:00:00). Returns the new appointment id and status.
        """
        from django.utils import timezone
        from django.utils.dateparse import parse_datetime
        from apps.doctors.models import Doctor
        from apps.appointments.models import Appointment

        # Guard against a guessed/stale id — guide the agent to re-search instead
        # of raising a foreign-key error.
        if not Doctor.objects.filter(pk=doctor_id).exists():
            return {'error': f'No doctor with id {doctor_id}. Call search_doctors '
                             f'to get the correct doctor id, then retry create_booking.'}

        dt = parse_datetime(scheduled_at)
        if dt is None:
            return {'error': 'Invalid datetime. Use ISO-8601, e.g. 2026-06-08T09:30:00.'}
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())

        try:
            appointment = Appointment.objects.create(
                patient_id=patient_id,
                doctor_id=doctor_id,
                scheduled_at=dt,
                reason=reason,
                appointment_type=appointment_type,
            )
        except Exception as exc:  # never bubble a DB error up as a 500
            return {'error': f'Could not create appointment: {exc}'}

        return {
            'appointment_id': appointment.pk,
            'status': appointment.status,
            'scheduled_at': dt.strftime('%Y-%m-%d %H:%M'),
        }

    @tool
    def cancel_booking(appointment_id: int) -> dict:
        """Cancel one of the current patient's appointments by its id."""
        from apps.appointments.models import Appointment

        try:
            appt = Appointment.objects.get(pk=appointment_id, patient_id=patient_id)
        except Appointment.DoesNotExist:
            return {'error': 'Appointment not found.'}

        if appt.status not in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED):
            return {'error': f'Cannot cancel appointment with status: {appt.status}'}

        appt.cancel()
        return {'appointment_id': appt.pk, 'status': appt.status}

    @tool
    def list_my_appointments() -> list[dict]:
        """List the current patient's upcoming appointments (id, doctor, date, status)."""
        from django.utils import timezone
        from apps.appointments.models import Appointment

        qs = (Appointment.objects
              .select_related('doctor__user')
              .filter(patient_id=patient_id, scheduled_at__gte=timezone.now())
              .exclude(status='cancelled')
              .order_by('scheduled_at')[:10])
        return [{
            'appointment_id': a.pk,
            'doctor': f"Dr. {a.doctor.user.get_full_name()}",
            'scheduled_at': a.scheduled_at.strftime('%Y-%m-%d %H:%M'),
            'status': a.status,
        } for a in qs]

    return [search_doctors, check_schedule, create_booking, cancel_booking, list_my_appointments]
