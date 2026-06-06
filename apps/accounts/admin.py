from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, PatientMemory


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('MediFlow', {'fields': ('role', 'phone', 'date_of_birth', 'avatar')}),
    )


@admin.register(PatientMemory)
class PatientMemoryAdmin(admin.ModelAdmin):
    list_display = ('patient', 'preferred_language', 'preferred_hospital', 'updated_at')
