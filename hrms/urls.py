from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.i18n import set_language

urlpatterns = [
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('employee/', include('employee.urls')),
    path('attendance/', include('attendance.urls')),
    path('leave/', include('leave.urls')),
    path('contract/', include('contract.urls')),
    path('salary/', include('salary.urls')),
    path('performance/', include('performance.urls')),
    path('training/', include('training.urls')),
    path('tasks/', include('tasks.urls')),
    path('assets/', include('assets.urls')),
    path('expenses/', include('expenses.urls')),
    path('documents/', include('documents.urls')),
    path('workflow/', include('workflow.urls')),
    path('notifications/', include('notifications.urls')),
    path('reports/', include('reports.urls')),
    path('settings/', include('settings.urls')),
    path('organization/', include('organization.urls')),
    path('search/', include('search.urls')),
    path('messaging/', include('messaging.urls')),
    path('api/', include('api.urls')),
    path('onboarding/', include('onboarding.urls')),
    
    # Language settings
    path('i18n/setlang/', set_language, name='set_language'),
    
    # Social authentication
    path('social-auth/', include('social_django.urls', namespace='social')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)