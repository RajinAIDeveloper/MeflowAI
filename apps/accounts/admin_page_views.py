"""Admin portal — server-rendered management pages (session auth, role=admin)."""
import logging

from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.appointments.models import Appointment
from apps.doctors.models import Doctor, Specialty

from .mixins import AdminRequiredMixin
from .models import User

logger = logging.getLogger(__name__)


def _reindex_doctor(request, doctor):
    """Embed a doctor into the pgvector knowledge base for AI triage/search.

    Best-effort: if embeddings are unavailable (e.g. the bge-small model can't
    load), the doctor is still saved — we just warn so an admin can run
    `python manage.py ingest_kb --doctor <pk>` later.
    """
    try:
        from apps.rag.ingest import ingest_doctor
        ingest_doctor(doctor)
    except Exception:
        logger.exception('Failed to embed doctor pk=%s into knowledge base', doctor.pk)
        messages.warning(
            request,
            'Doctor saved, but AI search indexing failed. Run '
            f'"python manage.py ingest_kb --doctor {doctor.pk}" to index them.',
        )


class AdminDashboardView(AdminRequiredMixin, View):
    def get(self, request):
        now = timezone.now()
        stats = {
            'patients': User.objects.filter(role=User.Role.PATIENT).count(),
            'doctors': User.objects.filter(role=User.Role.DOCTOR).count(),
            'appointments': Appointment.objects.count(),
            'upcoming': Appointment.objects.filter(scheduled_at__gte=now).exclude(status='cancelled').count(),
        }
        status_breakdown = (Appointment.objects
                            .values('status')
                            .annotate(n=Count('id'))
                            .order_by('-n'))
        recent_appointments = (Appointment.objects
                               .select_related('patient', 'doctor__user')
                               .order_by('-created_at')[:8])
        recent_users = User.objects.order_by('-date_joined')[:6]
        return render(request, 'admin_portal/dashboard.html', {
            'stats': stats,
            'status_breakdown': status_breakdown,
            'recent_appointments': recent_appointments,
            'recent_users': recent_users,
        })


class AdminDoctorsView(AdminRequiredMixin, View):
    def get(self, request):
        search = request.GET.get('search', '').strip()
        qs = Doctor.objects.select_related('user', 'specialty').order_by('user__last_name')
        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(specialty__name__icontains=search)
            )
        paginator = Paginator(qs, 15)
        page_obj = paginator.get_page(request.GET.get('page'))
        return render(request, 'admin_portal/doctors.html', {
            'doctors': page_obj, 'page_obj': page_obj, 'paginator': paginator,
            'is_paginated': paginator.num_pages > 1, 'search': search,
        })


class AdminDoctorCreateView(AdminRequiredMixin, View):
    def get(self, request):
        return render(request, 'admin_portal/doctor_form.html', {
            'specialties': Specialty.objects.all(), 'mode': 'create',
        })

    def post(self, request):
        email = request.POST.get('email', '').lower().strip()
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()

        ctx = {'specialties': Specialty.objects.all(), 'mode': 'create', 'data': request.POST}

        if not email or not first_name or not last_name:
            messages.error(request, 'Name and email are required.')
            return render(request, 'admin_portal/doctor_form.html', ctx)
        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'A user with this email already exists.')
            return render(request, 'admin_portal/doctor_form.html', ctx)
        try:
            validate_password(password)
        except ValidationError as e:
            messages.error(request, ' '.join(e.messages))
            return render(request, 'admin_portal/doctor_form.html', ctx)

        user = User.objects.create_user(
            username=email, email=email, password=password,
            first_name=first_name, last_name=last_name,
            phone=request.POST.get('phone', '').strip(),
            role=User.Role.DOCTOR,
        )
        doctor = Doctor.objects.create(
            user=user,
            specialty_id=request.POST.get('specialty') or None,
            hospital=request.POST.get('hospital', '').strip(),
            location=request.POST.get('location', '').strip(),
            bio=request.POST.get('bio', '').strip(),
            languages=request.POST.get('languages', '').strip() or 'English',
            years_experience=int(request.POST.get('years_experience') or 0),
            consultation_fee=request.POST.get('consultation_fee') or 0,
            is_available=request.POST.get('is_available') == 'on',
        )
        _reindex_doctor(request, doctor)
        messages.success(request, f'Doctor {user.get_full_name()} created.')
        return redirect('staff:doctors')


class AdminDoctorEditView(AdminRequiredMixin, View):
    def get(self, request, pk):
        doctor = get_object_or_404(Doctor.objects.select_related('user'), pk=pk)
        return render(request, 'admin_portal/doctor_form.html', {
            'specialties': Specialty.objects.all(), 'mode': 'edit', 'doctor': doctor,
        })

    def post(self, request, pk):
        doctor = get_object_or_404(Doctor.objects.select_related('user'), pk=pk)
        user = doctor.user
        user.first_name = request.POST.get('first_name', user.first_name).strip()
        user.last_name = request.POST.get('last_name', user.last_name).strip()
        user.phone = request.POST.get('phone', user.phone).strip()
        user.save(update_fields=['first_name', 'last_name', 'phone'])

        doctor.specialty_id = request.POST.get('specialty') or None
        doctor.hospital = request.POST.get('hospital', '').strip()
        doctor.location = request.POST.get('location', '').strip()
        doctor.bio = request.POST.get('bio', '').strip()
        doctor.languages = request.POST.get('languages', '').strip() or 'English'
        doctor.years_experience = int(request.POST.get('years_experience') or 0)
        doctor.consultation_fee = request.POST.get('consultation_fee') or 0
        doctor.is_available = request.POST.get('is_available') == 'on'
        doctor.save()
        _reindex_doctor(request, doctor)
        messages.success(request, 'Doctor updated.')
        return redirect('staff:doctors')


class AdminPatientsView(AdminRequiredMixin, View):
    def get(self, request):
        search = request.GET.get('search', '').strip()
        qs = User.objects.filter(role=User.Role.PATIENT).order_by('-date_joined')
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(email__icontains=search)
            )
        qs = qs.annotate(appt_count=Count('appointments'))
        paginator = Paginator(qs, 20)
        page_obj = paginator.get_page(request.GET.get('page'))
        return render(request, 'admin_portal/patients.html', {
            'patients': page_obj, 'page_obj': page_obj, 'paginator': paginator,
            'is_paginated': paginator.num_pages > 1, 'search': search,
        })


class AdminAppointmentsView(AdminRequiredMixin, View):
    def get(self, request):
        status_filter = request.GET.get('status', '').strip()
        qs = Appointment.objects.select_related('patient', 'doctor__user', 'doctor__specialty').order_by('-scheduled_at')
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = Paginator(qs, 20)
        page_obj = paginator.get_page(request.GET.get('page'))
        return render(request, 'admin_portal/appointments.html', {
            'appointments': page_obj, 'page_obj': page_obj, 'paginator': paginator,
            'is_paginated': paginator.num_pages > 1, 'status_filter': status_filter,
            'statuses': Appointment.Status.choices,
        })


class AdminSpecialtiesView(AdminRequiredMixin, View):
    def get(self, request):
        specialties = Specialty.objects.annotate(doctor_count=Count('doctors')).order_by('name')
        return render(request, 'admin_portal/specialties.html', {'specialties': specialties})

    def post(self, request):
        action = request.POST.get('action', 'add')
        if action == 'delete':
            Specialty.objects.filter(pk=request.POST.get('specialty_id')).delete()
            messages.success(request, 'Specialty removed.')
            return redirect('staff:specialties')

        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Specialty name is required.')
        elif Specialty.objects.filter(name__iexact=name).exists():
            messages.error(request, 'That specialty already exists.')
        else:
            Specialty.objects.create(
                name=name,
                description=request.POST.get('description', '').strip(),
                icon=request.POST.get('icon', '').strip(),
            )
            messages.success(request, f'Specialty "{name}" added.')
        return redirect('staff:specialties')


class AdminKnowledgeView(AdminRequiredMixin, View):
    """Manage the AI triage knowledge base: which doctors are embedded, and
    which documents have been ingested."""

    def get(self, request):
        from apps.rag.ingest import embedded_doctor_ids
        from apps.rag.models import KnowledgeDocument

        embedded = embedded_doctor_ids()
        doctors = (Doctor.objects.select_related('user', 'specialty')
                   .order_by('user__last_name'))
        doctor_rows = [{
            'pk': d.pk,
            'name': d.user.get_full_name() or d.user.email,
            'specialty': d.specialty.name if d.specialty_id else '—',
            'is_available': d.is_available,
            'embedded': d.pk in embedded,
        } for d in doctors]

        # Group non-doctor knowledge docs by their parent document.
        groups = {}
        for kd in (KnowledgeDocument.objects
                   .exclude(doc_type=KnowledgeDocument.DocType.DOCTOR_PROFILE)
                   .order_by('doc_type', 'source_id')):
            parent = (kd.metadata or {}).get('parent') or kd.source_id
            key = (kd.doc_type, parent)
            g = groups.setdefault(key, {
                'doc_type': kd.doc_type,
                'doc_type_label': kd.get_doc_type_display(),
                'parent': parent,
                'title': kd.title.split(' (part')[0],
                'filename': (kd.metadata or {}).get('filename', ''),
                'chunks': 0,
            })
            g['chunks'] += 1

        # Document types an admin can add (doctor profiles come from doctor records).
        doc_type_choices = [
            (value, label) for value, label in KnowledgeDocument.DocType.choices
            if value != KnowledgeDocument.DocType.DOCTOR_PROFILE
        ]

        return render(request, 'admin_portal/knowledge.html', {
            'doctor_rows': doctor_rows,
            'embedded_count': sum(1 for r in doctor_rows if r['embedded']),
            'doctor_total': len(doctor_rows),
            'documents': sorted(groups.values(), key=lambda x: (x['doc_type'], x['title'])),
            'doc_chunk_total': sum(g['chunks'] for g in groups.values()),
            'doc_type_choices': doc_type_choices,
        })

    @staticmethod
    def _read_upload(upload):
        """Extract text from an uploaded .txt/.md/.pdf file."""
        name = (upload.name or '').lower()
        if name.endswith('.pdf'):
            from pypdf import PdfReader  # raises ImportError if not installed
            reader = PdfReader(upload)
            return '\n\n'.join((page.extract_text() or '') for page in reader.pages)
        return upload.read().decode('utf-8', errors='ignore')

    def post(self, request):
        from django.utils.text import slugify

        from apps.rag.ingest import (
            ingest_doctor, ingest_doctor_profiles, ingest_text,
            remove_doctor, remove_document,
        )
        from apps.rag.models import KnowledgeDocument

        valid_doc_types = {
            v for v, _ in KnowledgeDocument.DocType.choices
            if v != KnowledgeDocument.DocType.DOCTOR_PROFILE
        }
        action = request.POST.get('action', '')

        try:
            if action == 'add_document':
                doc_type = request.POST.get('doc_type', '')
                title = request.POST.get('title', '').strip()
                content = request.POST.get('content', '').strip()
                upload = request.FILES.get('file')

                if doc_type not in valid_doc_types:
                    messages.error(request, 'Pick a valid document type.')
                    return redirect('staff:knowledge')

                if upload:
                    try:
                        content = self._read_upload(upload).strip()
                    except ImportError:
                        messages.error(request, 'PDF upload needs pypdf: pip install pypdf.')
                        return redirect('staff:knowledge')
                    except Exception:
                        messages.error(request, 'Could not read that file.')
                        return redirect('staff:knowledge')
                    if not title:
                        title = upload.name.rsplit('.', 1)[0].replace('_', ' ').title()

                if not title or not content:
                    messages.error(request, 'Provide a title and either pasted text or a file.')
                    return redirect('staff:knowledge')

                source_id = slugify(title) or 'document'
                docs = ingest_text(
                    title=title, content=content, doc_type=doc_type,
                    source_id=source_id,
                    metadata={'source': 'admin', 'filename': upload.name if upload else ''},
                )
                messages.success(request, f'Added "{title}" ({len(docs)} chunk(s)) to the knowledge base.')

            elif action == 'embed_all':
                ingest_doctor_profiles()
                messages.success(request, 'All doctors embedded into the triage index.')

            elif action == 'embed_selected':
                ids = request.POST.getlist('doctor_ids')
                if not ids:
                    messages.warning(request, 'No doctors selected.')
                else:
                    docs = Doctor.objects.select_related('user', 'specialty').filter(pk__in=ids)
                    for d in docs:
                        ingest_doctor(d)
                    messages.success(request, f'Embedded {docs.count()} doctor(s).')

            elif action == 'remove_selected':
                ids = request.POST.getlist('doctor_ids')
                removed = sum(remove_doctor(pk) for pk in ids)
                messages.success(request, f'Removed {removed} doctor profile(s) from the index.')

            elif action == 'remove_document':
                doc_type = request.POST.get('doc_type', '')
                parent = request.POST.get('parent', '')
                n = remove_document(doc_type, parent)
                messages.success(request, f'Removed document ({n} chunk(s)).')

            else:
                messages.error(request, 'Unknown action.')
        except Exception:
            logger.exception('Knowledge-base action failed: %s', action)
            messages.error(
                request,
                'Action failed — the embedding model may be unavailable. '
                'Check the server logs.',
            )
        return redirect('staff:knowledge')
