from django.urls import path
from . import views

urlpatterns = [
    # Notification views
    path('', views.notification_list, name='notification_list'),
    path('<int:notification_id>/', views.notification_detail, name='notification_detail'),
    path('<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    
    # API for AJAX requests
    path('get-unread-count/', views.get_unread_notification_count, name='get_unread_notification_count'),
    path('get-recent-notifications/', views.get_recent_notifications, name='get_recent_notifications'),
    path('settings/', views.notification_settings, name='notification_settings'),
]
