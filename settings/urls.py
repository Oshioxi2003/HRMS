from django.urls import path
from . import views

urlpatterns = [
    # System settings
    path('', views.system_settings, name='system_settings'),
    path('general/', views.general_settings, name='general_settings'),
    path('appearance/', views.appearance_settings, name='appearance_settings'),
    path('email/', views.email_settings, name='email_settings'),
    path('security/', views.security_settings, name='security_settings'),
    path('integration/', views.integration_settings, name='integration_settings'),
    
    # Module settings
    path('attendance/', views.attendance_settings, name='attendance_settings'),
    path('leave/', views.leave_settings, name='leave_settings'),
    path('performance/', views.performance_settings, name='performance_settings'),
    path('notification/', views.notification_settings, name='notification_settings'),
    
    # Setting management
    path('edit/<str:key>/', views.edit_setting, name='edit_setting'),
    path('create/', views.create_setting, name='create_setting'),
    path('delete/<str:key>/', views.delete_setting, name='delete_setting'),
    
    # Audit logs
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    path('audit-logs/user/<int:user_id>/', views.user_audit_logs, name='user_audit_logs'),
    
    # System info
    path('system-info/', views.system_info, name='system_info'),
    
    # Test email
    path('test-email/', views.test_email, name='test_email'),
]