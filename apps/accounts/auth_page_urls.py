from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import page_views

app_name = 'accounts'

urlpatterns = [
    path('login/',    page_views.LoginPageView.as_view(),    name='login'),
    path('register/', page_views.RegisterPageView.as_view(), name='register'),
    path('logout/',   page_views.LogoutPageView.as_view(),   name='logout'),

    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        success_url=reverse_lazy('accounts:password_reset_done'),
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html',
    ), name='password_reset_done'),

    path('password-reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete'),
    ), name='password_reset_confirm'),

    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html',
    ), name='password_reset_complete'),
]
