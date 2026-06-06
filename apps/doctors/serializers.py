from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from .models import Doctor, Specialty, AvailabilitySlot


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ('id', 'name', 'description', 'icon')


class AvailabilitySlotSerializer(serializers.ModelSerializer):
    day_label = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = AvailabilitySlot
        fields = ('id', 'day_of_week', 'day_label', 'start_time', 'end_time',
                  'slot_duration_minutes', 'is_active')


class DoctorListSerializer(serializers.ModelSerializer):
    specialty_name = serializers.CharField(source='specialty.name', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = Doctor
        fields = ('id', 'full_name', 'avatar', 'specialty_name', 'hospital',
                  'location', 'years_experience', 'consultation_fee',
                  'is_available', 'rating', 'total_reviews', 'languages')


class DoctorDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    specialty = SpecialtySerializer(read_only=True)
    availability_slots = AvailabilitySlotSerializer(many=True, read_only=True)

    class Meta:
        model = Doctor
        fields = ('id', 'user', 'specialty', 'hospital', 'location', 'bio',
                  'years_experience', 'consultation_fee', 'is_available',
                  'rating', 'total_reviews', 'languages', 'availability_slots')


class DoctorWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ('specialty', 'hospital', 'location', 'bio', 'years_experience',
                  'consultation_fee', 'is_available', 'languages')
