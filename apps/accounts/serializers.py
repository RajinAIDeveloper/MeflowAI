from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, PatientMemory


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name',
                  'password', 'password2', 'phone', 'date_of_birth', 'role')
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'role': {'read_only': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        email = validated_data['email'].lower()
        validated_data['username'] = email
        validated_data['email'] = email
        user = User.objects.create_user(**validated_data, role=User.Role.PATIENT)
        PatientMemory.objects.get_or_create(patient=user)
        return user


class MediFlowTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['full_name'] = user.get_full_name()
        return token


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'role', 'phone', 'date_of_birth', 'avatar')
        read_only_fields = ('id', 'role')


class PatientMemorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientMemory
        fields = ('preferred_language', 'preferred_hospital', 'preferred_doctor_id', 'notes')
