from django.db import models

from apps.accounts.models import User


class Specialty(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'specialties'
        verbose_name_plural = 'specialties'
        ordering = ['name']

    def __str__(self):
        return self.name


class Doctor(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='doctor_profile',
        limit_choices_to={'role': User.Role.DOCTOR},
    )
    specialty = models.ForeignKey(
        Specialty, on_delete=models.SET_NULL, null=True, related_name='doctors'
    )
    hospital = models.CharField(max_length=200)
    location = models.CharField(max_length=300, blank=True)
    bio = models.TextField(blank=True)
    years_experience = models.PositiveIntegerField(default=0)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    languages = models.CharField(max_length=200, default='English', blank=True)

    class Meta:
        db_table = 'doctors'
        ordering = ['-rating']

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} — {self.specialty}"


class AvailabilitySlot(models.Model):
    class Day(models.IntegerChoices):
        MONDAY = 0, 'Monday'
        TUESDAY = 1, 'Tuesday'
        WEDNESDAY = 2, 'Wednesday'
        THURSDAY = 3, 'Thursday'
        FRIDAY = 4, 'Friday'
        SATURDAY = 5, 'Saturday'
        SUNDAY = 6, 'Sunday'

    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name='availability_slots'
    )
    day_of_week = models.IntegerField(choices=Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration_minutes = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'availability_slots'
        ordering = ['day_of_week', 'start_time']
        unique_together = ('doctor', 'day_of_week', 'start_time')

    def __str__(self):
        return f"{self.doctor} | {self.get_day_of_week_display()} {self.start_time}"
