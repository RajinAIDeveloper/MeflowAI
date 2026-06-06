from django.urls import path

from .views import (
    AppointmentListView,
    BookAppointmentView,
    AppointmentDetailView,
    CancelAppointmentView,
    RescheduleAppointmentView,
)

urlpatterns = [
    path('', AppointmentListView.as_view(), name='appointment-list'),
    path('book/', BookAppointmentView.as_view(), name='appointment-book'),
    path('<int:pk>/', AppointmentDetailView.as_view(), name='appointment-detail'),
    path('<int:pk>/cancel/', CancelAppointmentView.as_view(), name='appointment-cancel'),
    path('<int:pk>/reschedule/', RescheduleAppointmentView.as_view(), name='appointment-reschedule'),
]
