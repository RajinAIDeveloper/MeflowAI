from django.contrib import admin

from .models import Specialty, Doctor, AvailabilitySlot


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name',)


class AvailabilitySlotInline(admin.TabularInline):
    model = AvailabilitySlot
    extra = 0


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialty', 'hospital', 'is_available', 'rating')
    list_filter = ('specialty', 'is_available')
    search_fields = ('user__first_name', 'user__last_name', 'hospital')
    inlines = [AvailabilitySlotInline]
