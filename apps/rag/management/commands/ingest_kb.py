"""
Management command: ingest_kb
Embed doctor profiles into the pgvector knowledge base so they appear in
AI triage / semantic search.

Usage:
    python manage.py ingest_kb                 # (re)embed ALL doctors
    python manage.py ingest_kb --doctor 12     # embed just one doctor (by Doctor pk)

Run it after adding or editing doctors. It is idempotent — existing rows are
updated in place (matched on doctor pk), so re-running is always safe.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.doctors.models import Doctor
from apps.rag.ingest import ingest_doctor, ingest_doctor_profiles


class Command(BaseCommand):
    help = 'Embed doctor profiles into the pgvector knowledge base.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--doctor', type=int, default=None,
            help='Ingest a single doctor by their Doctor pk (default: all doctors).',
        )

    def handle(self, *args, **options):
        doctor_pk = options['doctor']

        if doctor_pk is not None:
            try:
                doctor = Doctor.objects.select_related('user', 'specialty').get(pk=doctor_pk)
            except Doctor.DoesNotExist:
                raise CommandError(f'No Doctor with pk={doctor_pk}.')
            self.stdout.write(f'Embedding Dr. {doctor.user.get_full_name()} ...')
            ingest_doctor(doctor)
            self.stdout.write(self.style.SUCCESS('Done (1 doctor indexed).'))
            return

        self.stdout.write('Embedding all doctor profiles ...')
        ingest_doctor_profiles()
        count = Doctor.objects.count()
        self.stdout.write(self.style.SUCCESS(f'Done ({count} doctors indexed).'))
