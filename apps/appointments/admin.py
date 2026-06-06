from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'scheduled_at', 'status', 'appointment_type')
    list_filter = ('status', 'appointment_type')
    search_fields = ('patient__username', 'doctor__user__last_name')
    date_hierarchy = 'scheduled_at'
    readonly_fields = ('created_at', 'updated_at')
