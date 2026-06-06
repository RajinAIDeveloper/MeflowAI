from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Appointment
from .serializers import AppointmentSerializer, BookAppointmentSerializer, RescheduleSerializer


class AppointmentListView(generics.ListAPIView):
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Appointment.objects.select_related('patient', 'doctor__user', 'doctor__specialty')
        if user.is_patient:
            qs = qs.filter(patient=user)
        elif user.is_doctor:
            qs = qs.filter(doctor=user.doctor_profile)
        else:
            pass  # admin sees all

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class BookAppointmentView(generics.CreateAPIView):
    serializer_class = BookAppointmentSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        appointment = serializer.save()
        return Response(
            AppointmentSerializer(appointment).data,
            status=status.HTTP_201_CREATED,
        )


class AppointmentDetailView(generics.RetrieveAPIView):
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Appointment.objects.select_related('patient', 'doctor__user', 'doctor__specialty')
        if user.is_patient:
            return qs.filter(patient=user)
        if user.is_doctor:
            return qs.filter(doctor=user.doctor_profile)
        return qs


class CancelAppointmentView(APIView):
    def post(self, request, pk):
        appointment = self._get_appointment(request.user, pk)
        if appointment is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if appointment.status not in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED):
            return Response(
                {'detail': 'Only pending or confirmed appointments can be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        appointment.cancel()
        return Response(AppointmentSerializer(appointment).data)

    def _get_appointment(self, user, pk):
        try:
            qs = Appointment.objects.select_related('patient', 'doctor__user')
            if user.is_patient:
                return qs.get(pk=pk, patient=user)
            if user.is_doctor:
                return qs.get(pk=pk, doctor=user.doctor_profile)
            return qs.get(pk=pk)
        except Appointment.DoesNotExist:
            return None


class RescheduleAppointmentView(APIView):
    def post(self, request, pk):
        try:
            original = Appointment.objects.get(pk=pk, patient=request.user)
        except Appointment.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = RescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        original.status = Appointment.Status.RESCHEDULED
        original.save(update_fields=['status', 'updated_at'])

        new_appointment = Appointment.objects.create(
            patient=original.patient,
            doctor=original.doctor,
            scheduled_at=serializer.validated_data['scheduled_at'],
            duration_minutes=original.duration_minutes,
            appointment_type=original.appointment_type,
            reason=original.reason,
            rescheduled_from=original,
        )
        return Response(AppointmentSerializer(new_appointment).data, status=status.HTTP_201_CREATED)
