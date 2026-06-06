from django.urls import path
from . import page_views

app_name = 'patient'

urlpatterns = [
    path('',                        page_views.DashboardPageView.as_view(),         name='dashboard'),
    path('assistant/',              page_views.AiAssistantPageView.as_view(),       name='ai_assistant'),
    path('doctors/',                page_views.FindDoctorPageView.as_view(),        name='find_doctor'),
    path('doctors/<int:pk>/',       page_views.DoctorDetailPageView.as_view(),      name='doctor_detail'),
    path('doctors/<int:pk>/book/',  page_views.BookAppointmentPageView.as_view(),   name='book_appointment'),
    path('appointments/',           page_views.AppointmentsPageView.as_view(),      name='appointments'),
    path('appointments/<int:pk>/',  page_views.AppointmentDetailPageView.as_view(), name='appointment_detail'),
    path('triage/',                 page_views.TriagePageView.as_view(),            name='triage'),
    path('profile/',                page_views.ProfilePageView.as_view(),           name='profile'),
    path('help/',                   page_views.HelpPageView.as_view(),              name='help'),
]
