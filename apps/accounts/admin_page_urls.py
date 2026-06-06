from django.urls import path

from . import admin_page_views as views

app_name = 'staff'

urlpatterns = [
    path('',                       views.AdminDashboardView.as_view(),    name='dashboard'),
    path('doctors/',               views.AdminDoctorsView.as_view(),      name='doctors'),
    path('doctors/new/',           views.AdminDoctorCreateView.as_view(), name='doctor_create'),
    path('doctors/<int:pk>/edit/', views.AdminDoctorEditView.as_view(),   name='doctor_edit'),
    path('patients/',              views.AdminPatientsView.as_view(),     name='patients'),
    path('appointments/',          views.AdminAppointmentsView.as_view(), name='appointments'),
    path('specialties/',           views.AdminSpecialtiesView.as_view(),  name='specialties'),
    path('knowledge/',             views.AdminKnowledgeView.as_view(),    name='knowledge'),
]
