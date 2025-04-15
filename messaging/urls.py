from django.urls import path
from . import views

urlpatterns = [
    # Email templates
    path('email-templates/', views.email_template_list, name='email_template_list'),
    path('email-templates/create/', views.email_template_create, name='email_template_create'),
    path('email-templates/<int:template_id>/', views.email_template_detail, name='email_template_detail'),
    path('email-templates/<int:template_id>/edit/', views.email_template_edit, name='email_template_edit'),
    path('email-templates/<int:template_id>/delete/', views.email_template_delete, name='email_template_delete'),
    path('email-templates/<int:template_id>/preview/', views.email_template_preview, name='email_template_preview'),
    path('email-templates/<int:template_id>/test/', views.email_template_test, name='email_template_test'),
    
    # Email logs
    path('email-logs/', views.email_log_list, name='email_log_list'),
    path('email-logs/<int:log_id>/', views.email_log_detail, name='email_log_detail'),
    
    # Custom email
    path('send-custom-email/', views.send_custom_email, name='send_custom_email'),
]