from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        PATIENT = 'patient', 'Patient'
        DOCTOR = 'doctor', 'Doctor'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.PATIENT)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)

    class Meta:
        db_table = 'users'

    @property
    def is_patient(self):
        return self.role == self.Role.PATIENT

    @property
    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN


class PatientMemory(models.Model):
    """Stores per-patient preferences across sessions (preferred doctor/hospital/language)."""
    patient = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='memory',
        limit_choices_to={'role': User.Role.PATIENT},
    )
    preferred_language = models.CharField(max_length=10, default='en')
    preferred_hospital = models.CharField(max_length=200, blank=True)
    preferred_doctor_id = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'patient_memory'
        verbose_name_plural = 'patient memories'
