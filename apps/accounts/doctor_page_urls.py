from django.urls import path

from . import doctor_page_views as views

app_name = 'doctor'

urlpatterns = [
    path('',                          views.DoctorDashboardView.as_view(),         name='dashboard'),
    path('appointments/',             views.DoctorAppointmentsView.as_view(),      name='appointments'),
    path('appointments/<int:pk>/',    views.DoctorAppointmentDetailView.as_view(), name='appointment_detail'),
    path('availability/',             views.DoctorAvailabilityView.as_view(),      name='availability'),
    path('profile/',                  views.DoctorProfileView.as_view(),           name='profile'),
]
