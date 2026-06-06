from django.urls import path

from .views import (
    SpecialtyListView,
    DoctorListView,
    DoctorDetailView,
    DoctorProfileView,
    AvailabilitySlotListView,
    AvailabilitySlotDetailView,
    DoctorScheduleView,
)

urlpatterns = [
    path('specialties/', SpecialtyListView.as_view(), name='specialty-list'),
    path('', DoctorListView.as_view(), name='doctor-list'),
    path('<int:pk>/', DoctorDetailView.as_view(), name='doctor-detail'),
    path('<int:pk>/schedule/', DoctorScheduleView.as_view(), name='doctor-schedule'),
    path('me/', DoctorProfileView.as_view(), name='doctor-me'),
    path('me/availability/', AvailabilitySlotListView.as_view(), name='doctor-availability-list'),
    path('me/availability/<int:pk>/', AvailabilitySlotDetailView.as_view(), name='doctor-availability-detail'),
]
