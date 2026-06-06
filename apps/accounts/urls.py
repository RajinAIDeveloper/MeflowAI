from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    MediFlowTokenObtainPairView,
    MeView,
    LogoutView,
    PatientMemoryView,
    ChangePasswordView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', MediFlowTokenObtainPairView.as_view(), name='auth-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('me/memory/', PatientMemoryView.as_view(), name='auth-patient-memory'),
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
]
