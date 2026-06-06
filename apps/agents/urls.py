from django.urls import path

from .views import TriageView, BookingChatView

urlpatterns = [
    path('triage/', TriageView.as_view(), name='agent-triage'),
    path('chat/', BookingChatView.as_view(), name='agent-booking-chat'),
]
