"""
Management command: seed_data
Creates all demo accounts, doctors, specialties, availability slots,
and sample appointments needed to test every workflow in MediFlow AI.

Usage:
    python manage.py seed_data            # create everything (idempotent)
    python manage.py seed_data --flush    # delete ALL existing data first
"""
import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import PatientMemory
from apps.appointments.models import Appointment
from apps.doctors.models import AvailabilitySlot, Doctor, Specialty

User = get_user_model()

# ── Credentials (printed to console on completion) ──────────────────────────
ADMIN_EMAIL    = 'admin@mediflow.dev'
PATIENT_EMAIL  = 'patient@mediflow.dev'
PATIENT2_EMAIL = 'patient2@mediflow.dev'
DOCTOR_EMAILS  = [
    'dr.sarah.chen@mediflow.dev',
    'dr.james.okafor@mediflow.dev',
    'dr.priya.nair@mediflow.dev',
    'dr.alex.novak@mediflow.dev',
]
DEFAULT_PASS = 'MediFlow2024!'


class Command(BaseCommand):
    help = 'Seed demo data for development and testing.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush', action='store_true',
            help='Delete all existing users, doctors, appointments before seeding.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['flush']:
            self.stdout.write('Flushing existing data...')
            Appointment.objects.all().delete()
            AvailabilitySlot.objects.all().delete()
            Doctor.objects.all().delete()
            PatientMemory.objects.all().delete()
            User.objects.exclude(is_superuser=True).delete()
            Specialty.objects.all().delete()
            self.stdout.write(self.style.WARNING('Data flushed.'))

        # ── 1. Specialties ───────────────────────────────────────────────────
        self.stdout.write('Creating specialties...')
        specialties_data = [
            ('Cardiology',        'cardiology',          'Heart and cardiovascular system.'),
            ('Neurology',         'neurology',           'Brain and nervous system disorders.'),
            ('Orthopedics',       'orthopedics',         'Bones, joints, and musculoskeletal system.'),
            ('Dermatology',       'dermatology',         'Skin, hair, and nail conditions.'),
            ('Pediatrics',        'child_care',          'Medical care for infants and children.'),
            ('General Practice',  'medical_services',    'Primary care and general health.'),
        ]
        specs = {}
        for name, icon, desc in specialties_data:
            s, _ = Specialty.objects.get_or_create(name=name, defaults={'icon': icon, 'description': desc})
            specs[name] = s

        # ── 2. Admin user ────────────────────────────────────────────────────
        self.stdout.write('Creating admin user...')
        admin, _ = User.objects.get_or_create(
            email__iexact=ADMIN_EMAIL,
            defaults={
                'username':   ADMIN_EMAIL,
                'email':      ADMIN_EMAIL,
                'first_name': 'Alex',
                'last_name':  'Admin',
                'role':       User.Role.ADMIN,
                'is_staff':   True,
            },
        )
        admin.set_password(DEFAULT_PASS)
        admin.save()

        # ── 3. Patient 1 (primary test patient) ──────────────────────────────
        self.stdout.write('Creating patients...')
        patient, _ = User.objects.get_or_create(
            email__iexact=PATIENT_EMAIL,
            defaults={
                'username':      PATIENT_EMAIL,
                'email':         PATIENT_EMAIL,
                'first_name':    'Sarah',
                'last_name':     'Mitchell',
                'phone':         '+1 555 010 0001',
                'date_of_birth': datetime.date(1990, 6, 15),
                'role':          User.Role.PATIENT,
            },
        )
        patient.set_password(DEFAULT_PASS)
        patient.save()
        mem, _ = PatientMemory.objects.get_or_create(patient=patient)
        mem.preferred_language = 'en'
        mem.preferred_hospital = 'City General Hospital'
        mem.notes = 'Allergic to penicillin. Prefers morning appointments.'
        mem.save()

        # ── 4. Patient 2 (for appointment variety) ───────────────────────────
        patient2, _ = User.objects.get_or_create(
            email__iexact=PATIENT2_EMAIL,
            defaults={
                'username':      PATIENT2_EMAIL,
                'email':         PATIENT2_EMAIL,
                'first_name':    'Marcus',
                'last_name':     'Rivera',
                'phone':         '+1 555 010 0002',
                'date_of_birth': datetime.date(1985, 3, 22),
                'role':          User.Role.PATIENT,
            },
        )
        patient2.set_password(DEFAULT_PASS)
        patient2.save()
        PatientMemory.objects.get_or_create(patient=patient2)

        # ── 5. Doctors ───────────────────────────────────────────────────────
        self.stdout.write('Creating doctors...')
        doctors_data = [
            {
                'email': 'dr.sarah.chen@mediflow.dev',
                'first_name': 'Sarah', 'last_name': 'Chen',
                'phone': '+1 555 020 0001',
                'specialty': 'Cardiology',
                'hospital': 'City General Hospital',
                'location': 'Building A, Floor 4',
                'bio': 'Board-certified cardiologist with 12 years of experience in interventional cardiology and heart failure management.',
                'years_experience': 12,
                'consultation_fee': 250.00,
                'languages': 'English, Mandarin',
                'rating': 4.9,
                'is_available': True,
            },
            {
                'email': 'dr.james.okafor@mediflow.dev',
                'first_name': 'James', 'last_name': 'Okafor',
                'phone': '+1 555 020 0002',
                'specialty': 'Neurology',
                'hospital': 'Metro Health Center',
                'location': 'Neurology Wing, Room 201',
                'bio': 'Specialist in epilepsy, migraine, and stroke rehabilitation. Committed to evidence-based, patient-centered care.',
                'years_experience': 9,
                'consultation_fee': 220.00,
                'languages': 'English, Yoruba',
                'rating': 4.7,
                'is_available': True,
            },
            {
                'email': 'dr.priya.nair@mediflow.dev',
                'first_name': 'Priya', 'last_name': 'Nair',
                'phone': '+1 555 020 0003',
                'specialty': 'Dermatology',
                'hospital': 'Westside Dermatology Clinic',
                'location': 'Suite 12B',
                'bio': 'Expert in acne, eczema, psoriasis, and cosmetic dermatology. Fluent in English and Malayalam.',
                'years_experience': 7,
                'consultation_fee': 175.00,
                'languages': 'English, Malayalam',
                'rating': 4.8,
                'is_available': True,
            },
            {
                'email': 'dr.alex.novak@mediflow.dev',
                'first_name': 'Alex', 'last_name': 'Novak',
                'phone': '+1 555 020 0004',
                'specialty': 'General Practice',
                'hospital': 'Downtown Family Clinic',
                'location': 'Ground Floor',
                'bio': 'Friendly GP providing comprehensive primary care for all ages. Accepting new patients.',
                'years_experience': 5,
                'consultation_fee': 120.00,
                'languages': 'English, Czech',
                'rating': 4.6,
                'is_available': False,  # one unavailable doc to test that filter
            },
        ]

        doctor_objects = {}
        for d in doctors_data:
            u, _ = User.objects.get_or_create(
                email__iexact=d['email'],
                defaults={
                    'username':   d['email'],
                    'email':      d['email'],
                    'first_name': d['first_name'],
                    'last_name':  d['last_name'],
                    'phone':      d['phone'],
                    'role':       User.Role.DOCTOR,
                },
            )
            u.set_password(DEFAULT_PASS)
            u.save()

            doc, _ = Doctor.objects.get_or_create(
                user=u,
                defaults={
                    'specialty':         specs[d['specialty']],
                    'hospital':          d['hospital'],
                    'location':          d['location'],
                    'bio':               d['bio'],
                    'years_experience':  d['years_experience'],
                    'consultation_fee':  d['consultation_fee'],
                    'languages':         d['languages'],
                    'rating':            d['rating'],
                    'is_available':      d['is_available'],
                },
            )
            doctor_objects[d['email']] = doc

        # ── 6. Availability slots ────────────────────────────────────────────
        self.stdout.write('Creating availability slots...')
        # Dr. Chen — Mon/Wed/Fri 09:00-17:00, 30-min slots
        chen = doctor_objects['dr.sarah.chen@mediflow.dev']
        for day in [0, 2, 4]:  # Mon, Wed, Fri
            AvailabilitySlot.objects.get_or_create(
                doctor=chen, day_of_week=day, start_time=datetime.time(9, 0),
                defaults={'end_time': datetime.time(17, 0), 'slot_duration_minutes': 30, 'is_active': True},
            )

        # Dr. Okafor — Tue/Thu 08:00-16:00, 45-min slots
        okafor = doctor_objects['dr.james.okafor@mediflow.dev']
        for day in [1, 3]:  # Tue, Thu
            AvailabilitySlot.objects.get_or_create(
                doctor=okafor, day_of_week=day, start_time=datetime.time(8, 0),
                defaults={'end_time': datetime.time(16, 0), 'slot_duration_minutes': 45, 'is_active': True},
            )

        # Dr. Nair — Mon-Thu 10:00-18:00, 30-min slots
        nair = doctor_objects['dr.priya.nair@mediflow.dev']
        for day in [0, 1, 2, 3]:  # Mon-Thu
            AvailabilitySlot.objects.get_or_create(
                doctor=nair, day_of_week=day, start_time=datetime.time(10, 0),
                defaults={'end_time': datetime.time(18, 0), 'slot_duration_minutes': 30, 'is_active': True},
            )

        # Dr. Novak — unavailable, but still has slots (tests slot-loading edge case)
        novak = doctor_objects['dr.alex.novak@mediflow.dev']
        AvailabilitySlot.objects.get_or_create(
            doctor=novak, day_of_week=0, start_time=datetime.time(9, 0),
            defaults={'end_time': datetime.time(12, 0), 'slot_duration_minutes': 30, 'is_active': True},
        )

        # ── 7. Sample appointments ───────────────────────────────────────────
        self.stdout.write('Creating sample appointments...')
        now = timezone.now()

        def future(days, hour=10, minute=0):
            d = now + datetime.timedelta(days=days)
            return d.replace(hour=hour, minute=minute, second=0, microsecond=0)

        def past(days, hour=14, minute=0):
            d = now - datetime.timedelta(days=days)
            return d.replace(hour=hour, minute=minute, second=0, microsecond=0)

        appts = [
            # ── Patient 1: upcoming confirmed ──
            dict(
                patient=patient, doctor=chen,
                scheduled_at=future(3, 10, 0),
                duration_minutes=30,
                appointment_type=Appointment.AppointmentType.IN_PERSON,
                status=Appointment.Status.CONFIRMED,
                reason='Annual cardiac check-up',
                patient_notes='Please bring previous ECG results.',
            ),
            # ── Patient 1: upcoming pending ──
            dict(
                patient=patient, doctor=nair,
                scheduled_at=future(7, 11, 0),
                duration_minutes=30,
                appointment_type=Appointment.AppointmentType.IN_PERSON,
                status=Appointment.Status.PENDING,
                reason='Skin rash on forearm — started 2 weeks ago',
            ),
            # ── Patient 1: upcoming virtual ──
            dict(
                patient=patient, doctor=okafor,
                scheduled_at=future(14, 9, 0),
                duration_minutes=45,
                appointment_type=Appointment.AppointmentType.VIRTUAL,
                status=Appointment.Status.CONFIRMED,
                reason='Recurring migraines — follow-up on MRI results',
                patient_notes='Will connect via laptop.',
            ),
            # ── Patient 1: past completed ──
            dict(
                patient=patient, doctor=chen,
                scheduled_at=past(10, 14, 30),
                duration_minutes=30,
                appointment_type=Appointment.AppointmentType.IN_PERSON,
                status=Appointment.Status.COMPLETED,
                reason='Chest pain evaluation',
                doctor_notes='ECG normal. Stress test recommended. Follow up in 3 months.',
            ),
            # ── Patient 1: past cancelled ──
            dict(
                patient=patient, doctor=nair,
                scheduled_at=past(5, 11, 0),
                duration_minutes=30,
                appointment_type=Appointment.AppointmentType.IN_PERSON,
                status=Appointment.Status.CANCELLED,
                reason='Eczema flare-up',
            ),
            # ── Patient 2: various ──
            dict(
                patient=patient2, doctor=chen,
                scheduled_at=future(2, 15, 0),
                duration_minutes=30,
                appointment_type=Appointment.AppointmentType.IN_PERSON,
                status=Appointment.Status.PENDING,
                reason='Palpitations — first occurrence',
            ),
            dict(
                patient=patient2, doctor=okafor,
                scheduled_at=past(20, 10, 0),
                duration_minutes=45,
                appointment_type=Appointment.AppointmentType.IN_PERSON,
                status=Appointment.Status.COMPLETED,
                reason='Dizziness and headache',
                doctor_notes='Migraine with aura. Prescribed sumatriptan 50mg.',
            ),
        ]

        for a in appts:
            # Idempotent: match on patient + doctor + scheduled_at
            Appointment.objects.get_or_create(
                patient=a['patient'],
                doctor=a['doctor'],
                scheduled_at=a['scheduled_at'],
                defaults={k: v for k, v in a.items() if k not in ('patient', 'doctor', 'scheduled_at')},
            )

        # ── Summary ──────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  MediFlow AI — Seed Data Created'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('  ADMIN'))
        self.stdout.write(f'    Email:    {ADMIN_EMAIL}')
        self.stdout.write(f'    Password: {DEFAULT_PASS}')
        self.stdout.write(f'    Portal:   http://localhost:8000/staff/')
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('  PATIENT (primary)'))
        self.stdout.write(f'    Email:    {PATIENT_EMAIL}')
        self.stdout.write(f'    Password: {DEFAULT_PASS}')
        self.stdout.write(f'    Portal:   http://localhost:8000/')
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('  PATIENT 2'))
        self.stdout.write(f'    Email:    {PATIENT2_EMAIL}')
        self.stdout.write(f'    Password: {DEFAULT_PASS}')
        self.stdout.write(f'    Portal:   http://localhost:8000/')
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('  DOCTORS'))
        for email in DOCTOR_EMAILS:
            self.stdout.write(f'    {email}')
        self.stdout.write(f'    Password: {DEFAULT_PASS} (all doctors)')
        self.stdout.write(f'    Portal:   http://localhost:8000/doctor/')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
