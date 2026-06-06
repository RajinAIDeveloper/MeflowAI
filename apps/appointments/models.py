from django.db import models

from apps.accounts.models import User
from apps.doctors.models import Doctor


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'
        COMPLETED = 'completed', 'Completed'
        RESCHEDULED = 'rescheduled', 'Rescheduled'

    class AppointmentType(models.TextChoices):
        IN_PERSON = 'in_person', 'In Person'
        VIRTUAL = 'virtual', 'Virtual'

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='appointments',
        limit_choices_to={'role': User.Role.PATIENT},
    )
    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name='appointments'
    )
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    appointment_type = models.CharField(
        max_length=20, choices=AppointmentType.choices,
        default=AppointmentType.IN_PERSON,
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    reason = models.TextField(blank=True)
    patient_notes = models.TextField(blank=True)
    doctor_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Tracks which appointment this was rescheduled from
    rescheduled_from = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='rescheduled_to',
    )

    class Meta:
        db_table = 'appointments'
        ordering = ['-scheduled_at']

    def __str__(self):
        return (f"{self.patient.get_full_name()} → Dr. "
                f"{self.doctor.user.get_full_name()} @ {self.scheduled_at:%Y-%m-%d %H:%M}")

    def cancel(self):
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status', 'updated_at'])

    def confirm(self):
        self.status = self.Status.CONFIRMED
        self.save(update_fields=['status', 'updated_at'])
