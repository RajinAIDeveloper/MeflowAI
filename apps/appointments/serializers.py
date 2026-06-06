from django.utils import timezone
from rest_framework import serializers

from apps.doctors.serializers import DoctorListSerializer
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_detail = DoctorListSerializer(source='doctor', read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_appointment_type_display', read_only=True)

    class Meta:
        model = Appointment
        fields = (
            'id', 'patient', 'patient_name', 'doctor', 'doctor_detail',
            'scheduled_at', 'duration_minutes', 'appointment_type', 'type_display',
            'status', 'status_display', 'reason', 'patient_notes', 'doctor_notes',
            'created_at', 'updated_at', 'rescheduled_from',
        )
        read_only_fields = ('id', 'patient', 'status', 'created_at', 'updated_at')


class BookAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ('doctor', 'scheduled_at', 'duration_minutes',
                  'appointment_type', 'reason', 'patient_notes')

    def validate_scheduled_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError('Appointment must be scheduled in the future.')
        return value

    def create(self, validated_data):
        validated_data['patient'] = self.context['request'].user
        return super().create(validated_data)


class RescheduleSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField()

    def validate_scheduled_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError('New time must be in the future.')
        return value
