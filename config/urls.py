from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Page views (Django-template frontend) ──
    path('', include('apps.accounts.auth_page_urls')),       # /login/ /register/ /logout/
    path('doctor/', include('apps.accounts.doctor_page_urls')),  # doctor portal
    path('staff/', include('apps.accounts.admin_page_urls')),    # admin portal
    path('', include('apps.accounts.patient_page_urls')),    # / /assistant/ /doctors/ etc.

    # ── REST API ──
    path('api/auth/',        include('apps.accounts.urls')),
    path('api/doctors/',     include('apps.doctors.urls')),
    path('api/appointments/', include('apps.appointments.urls')),
    path('api/rag/',         include('apps.rag.urls')),
    path('api/agents/',      include('apps.agents.urls')),
    path('api/evaluation/',  include('apps.evaluation.urls')),
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    except ImportError:
        pass
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
