import datetime as dt

from django.utils import timezone
from rest_framework import generics, permissions, filters, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.appointments.models import Appointment
from .models import Doctor, Specialty, AvailabilitySlot
from .serializers import (
    DoctorListSerializer,
    DoctorDetailSerializer,
    DoctorWriteSerializer,
    SpecialtySerializer,
    AvailabilitySlotSerializer,
)
from .permissions import IsAdminUser, IsDoctor, IsDoctorOwner


class SpecialtyListView(generics.ListAPIView):
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer
    permission_classes = (permissions.AllowAny,)


class DoctorListView(generics.ListAPIView):
    serializer_class = DoctorListSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__first_name', 'user__last_name', 'specialty__name', 'hospital']
    ordering_fields = ['rating', 'years_experience', 'consultation_fee']

    def get_queryset(self):
        qs = Doctor.objects.select_related('user', 'specialty')
        specialty = self.request.query_params.get('specialty')
        available = self.request.query_params.get('available')
        hospital = self.request.query_params.get('hospital')
        if specialty:
            qs = qs.filter(specialty__name__icontains=specialty)
        if available == 'true':
            qs = qs.filter(is_available=True)
        if hospital:
            qs = qs.filter(hospital__icontains=hospital)
        return qs


class DoctorDetailView(generics.RetrieveAPIView):
    queryset = Doctor.objects.select_related('user', 'specialty').prefetch_related('availability_slots')
    serializer_class = DoctorDetailSerializer
    permission_classes = (permissions.AllowAny,)


class DoctorProfileView(generics.RetrieveUpdateAPIView):
    """Doctor edits their own profile."""
    permission_classes = (permissions.IsAuthenticated, IsDoctorOwner)

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return DoctorWriteSerializer
        return DoctorDetailSerializer

    def get_object(self):
        return self.request.user.doctor_profile


class AvailabilitySlotListView(generics.ListCreateAPIView):
    serializer_class = AvailabilitySlotSerializer
    permission_classes = (IsDoctor,)

    def get_queryset(self):
        return AvailabilitySlot.objects.filter(
            doctor=self.request.user.doctor_profile
        )

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user.doctor_profile)


class AvailabilitySlotDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AvailabilitySlotSerializer
    permission_classes = (IsDoctorOwner,)

    def get_queryset(self):
        return AvailabilitySlot.objects.filter(
            doctor=self.request.user.doctor_profile
        )


class DoctorScheduleView(APIView):
    """Return available time slots for a doctor on a given date."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        doctor = get_object_or_404(Doctor, pk=pk)

        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'detail': 'date parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target_date = dt.date.fromisoformat(date_str)
        except ValueError:
            return Response({'detail': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        weekday = target_date.weekday()  # Mon=0, Sun=6 — matches AvailabilitySlot.Day

        slots_qs = AvailabilitySlot.objects.filter(
            doctor=doctor, day_of_week=weekday, is_active=True
        )

        # Collect already-booked times for this doctor on this date
        booked_times = set()
        for appt in Appointment.objects.filter(
            doctor=doctor,
            scheduled_at__date=target_date,
        ).exclude(status='cancelled'):
            local_dt = timezone.localtime(appt.scheduled_at)
            booked_times.add(local_dt.strftime('%H:%M'))

        now_local = timezone.localtime(timezone.now())
        is_today = (target_date == now_local.date())

        available = []
        for slot in slots_qs:
            duration = slot.slot_duration_minutes or 30
            current = dt.datetime.combine(target_date, slot.start_time)
            end = dt.datetime.combine(target_date, slot.end_time)
            while current < end:
                time_str = current.strftime('%H:%M')
                if time_str not in booked_times:
                    if not is_today or current.time() > now_local.time():
                        available.append(time_str)
                current += dt.timedelta(minutes=duration)

        return Response({'available_slots': sorted(set(available))})
