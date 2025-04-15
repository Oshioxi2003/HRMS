from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.utils import timezone
import platform
import json
import sys
import os
from .models import SystemSetting, AuditLog
from .forms import SystemSettingForm
from .services import SettingsService, AuditService
from accounts.decorators import admin_required

@login_required
@admin_required
def system_settings(request):
    """Main system settings dashboard"""
    # Get counts of settings by group
    setting_counts = {}
    for group_key, group_name in SystemSetting.SETTING_GROUP_CHOICES:
        count = SystemSetting.objects.filter(group=group_key).count()
        setting_counts[group_key] = count
    
    # Get recent audit logs
    recent_logs = AuditService.get_recent_logs(limit=5)
    
    return render(request, 'settings/system_settings.html', {
        'setting_counts': setting_counts,
        'recent_logs': recent_logs,
        'group_choices': SystemSetting.SETTING_GROUP_CHOICES
    })

@login_required
@admin_required
def general_settings(request):
    """General system settings"""
    if request.method == 'POST':
        # Handle bulk update of settings
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                try:
                    setting = SystemSetting.objects.get(key=setting_key)
                    setting.value = value
                    setting.save()
                    
                    # Clear cache for this setting
                    cache_key = f"{SettingsService.CACHE_KEY_PREFIX}{setting_key}"
                    SettingsService.delete_setting(setting_key)
                except SystemSetting.DoesNotExist:
                    continue
        
        messages.success(request, "General settings updated successfully.")
        return redirect('general_settings')
    
    # Get general settings
    settings_list = SettingsService.get_settings_by_group('general')
    
    return render(request, 'settings/general_settings.html', {
        'settings': settings_list,
        'current_group': 'general'
    })

@login_required
@admin_required
def appearance_settings(request):
    """Appearance settings"""
    if request.method == 'POST':
        # Handle bulk update of settings
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                try:
                    setting = SystemSetting.objects.get(key=setting_key)
                    setting.value = value
                    setting.save()
                    
                    # Clear cache for this setting
                    SettingsService.delete_setting(setting_key)
                except SystemSetting.DoesNotExist:
                    continue
        
        messages.success(request, "Appearance settings updated successfully.")
        return redirect('appearance_settings')
    
    # Get appearance settings
    settings_list = SettingsService.get_settings_by_group('appearance')
    
    # Create default appearance settings if none exist
    if not settings_list.exists():
        default_settings = [
            {
                'key': 'company_logo', 
                'name': 'Company Logo URL', 
                'value': '/static/img/default-logo.png',
                'value_type': 'string',
                'description': 'URL to the company logo image',
                'is_public': True
            },
            {
                'key': 'primary_color', 
                'name': 'Primary Color', 
                'value': '#3f51b5',
                'value_type': 'string',
                'description': 'Primary color for UI elements',
                'is_public': True
            },
            {
                'key': 'secondary_color', 
                'name': 'Secondary Color', 
                'value': '#f50057',
                'value_type': 'string',
                'description': 'Secondary color for UI elements',
                'is_public': True
            },
            {
                'key': 'enable_dark_mode', 
                'name': 'Enable Dark Mode', 
                'value': 'false',
                'value_type': 'boolean',
                'description': 'Allow users to switch to dark mode',
                'is_public': True
            }
        ]
        
        for setting_data in default_settings:
            SettingsService.set_setting(
                key=setting_data['key'],
                value=setting_data['value'],
                value_type=setting_data['value_type'],
                name=setting_data['name'],
                description=setting_data['description'],
                group='appearance',
                is_public=setting_data['is_public']
            )
        
        # Refresh settings list
        settings_list = SettingsService.get_settings_by_group('appearance')
    
    return render(request, 'settings/appearance_settings.html', {
        'settings': settings_list,
        'current_group': 'appearance'
    })

@login_required
@admin_required
def email_settings(request):
    """Email settings"""
    if request.method == 'POST':
        # Handle bulk update of settings
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                try:
                    setting = SystemSetting.objects.get(key=setting_key)
                    setting.value = value
                    setting.save()
                    
                    # Clear cache for this setting
                    SettingsService.delete_setting(setting_key)
                except SystemSetting.DoesNotExist:
                    continue
        
        messages.success(request, "Email settings updated successfully.")
        return redirect('email_settings')
    
    # Get email settings
    settings_list = SettingsService.get_settings_by_group('email')
    
    # Create default email settings if none exist
    if not settings_list.exists():
        default_settings = [
            {
                'key': 'email_host', 
                'name': 'Email Host', 
                'value': 'smtp.example.com',
                'value_type': 'string',
                'description': 'SMTP server hostname'
            },
            {
                'key': 'email_port', 
                'name': 'Email Port', 
                'value': '587',
                'value_type': 'integer',
                'description': 'SMTP server port'
            },
            {
                'key': 'email_use_tls', 
                'name': 'Use TLS', 
                'value': 'true',
                'value_type': 'boolean',
                'description': 'Use TLS for SMTP connection'
            },
            {
                'key': 'email_host_user', 
                'name': 'Email Username', 
                'value': 'user@example.com',
                'value_type': 'string',
                'description': 'SMTP server username'
            },
            {
                'key': 'email_host_password', 
                'name': 'Email Password', 
                'value': '',
                'value_type': 'string',
                'description': 'SMTP server password'
            },
            {
                'key': 'default_from_email', 
                'name': 'Default From Email', 
                'value': 'hrms@example.com',
                'value_type': 'string',
                'description': 'Default sender email address'
            }
        ]
        
        for setting_data in default_settings:
            SettingsService.set_setting(
                key=setting_data['key'],
                value=setting_data['value'],
                value_type=setting_data['value_type'],
                name=setting_data['name'],
                description=setting_data['description'],
                group='email'
            )
        
        # Refresh settings list
        settings_list = SettingsService.get_settings_by_group('email')
    
    return render(request, 'settings/email_settings.html', {
        'settings': settings_list,
        'current_group': 'email'
    })

@login_required
@admin_required
def security_settings(request):
    """Security settings"""
    if request.method == 'POST':
        # Handle bulk update of settings
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                try:
                    setting = SystemSetting.objects.get(key=setting_key)
                    setting.value = value
                    setting.save()
                    
                    # Clear cache for this setting
                    SettingsService.delete_setting(setting_key)
                except SystemSetting.DoesNotExist:
                    continue
        
        messages.success(request, "Security settings updated successfully.")
        return redirect('security_settings')
    
    # Get security settings
    settings_list = SettingsService.get_settings_by_group('security')
    
    # Create default security settings if none exist
    if not settings_list.exists():
        default_settings = [
            {
                'key': 'password_expiry_days', 
                'name': 'Password Expiry (Days)', 
                'value': '90',
                'value_type': 'integer',
                'description': 'Number of days before passwords expire (0 to disable)'
            },
            {
                'key': 'min_password_length', 
                'name': 'Minimum Password Length', 
                'value': '8',
                'value_type': 'integer',
                'description': 'Minimum number of characters for passwords'
            },
            {
                'key': 'password_complexity', 
                'name': 'Require Complex Passwords', 
                'value': 'true',
                'value_type': 'boolean',
                'description': 'Require passwords to contain letters, numbers, and special characters'
            },
            {
                'key': 'max_login_attempts', 
                'name': 'Max Login Attempts', 
                'value': '5',
                'value_type': 'integer',
                'description': 'Number of failed login attempts before account lockout'
            },
            {
                'key': 'session_timeout_minutes', 
                'name': 'Session Timeout (Minutes)', 
                'value': '60',
                'value_type': 'integer',
                'description': 'Minutes of inactivity before session expires'
            },
            {
                'key': 'enable_2fa', 
                'name': 'Enable Two-Factor Authentication', 
                'value': 'false',
                'value_type': 'boolean',
                'description': 'Enable two-factor authentication for users'
            }
        ]
        
        for setting_data in default_settings:
            SettingsService.set_setting(
                key=setting_data['key'],
                value=setting_data['value'],
                value_type=setting_data['value_type'],
                name=setting_data['name'],
                description=setting_data['description'],
                group='security'
            )
        
        # Refresh settings list
        settings_list = SettingsService.get_settings_by_group('security')
    
    return render(request, 'settings/security_settings.html', {
        'settings': settings_list,
        'current_group': 'security'
    })

@login_required
@admin_required
def integration_settings(request):
    """Integration settings"""
    if request.method == 'POST':
        # Handle bulk update of settings
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                try:
                    setting = SystemSetting.objects.get(key=setting_key)
                    setting.value = value
                    setting.save()
                    
                    # Clear cache for this setting
                    SettingsService.delete_setting(setting_key)
                except SystemSetting.DoesNotExist:
                    continue
        
        messages.success(request, "Integration settings updated successfully.")
        return redirect('integration_settings')
    
    # Get integration settings
    settings_list = SettingsService.get_settings_by_group('integration')
    
    # Create default integration settings if none exist
    if not settings_list.exists():
        default_settings = [
            {
                'key': 'google_client_id', 
                'name': 'Google OAuth Client ID', 
                'value': '',
                'value_type': 'string',
                'description': 'Google OAuth client ID for login integration'
            },
            {
                'key': 'google_client_secret', 
                'name': 'Google OAuth Client Secret', 
                'value': '',
                'value_type': 'string',
                'description': 'Google OAuth client secret'
            },
            {
                'key': 'enable_google_login', 
                'name': 'Enable Google Login', 
                'value': 'false',
                'value_type': 'boolean',
                'description': 'Allow users to sign in with Google accounts'
            },
            {
                'key': 'slack_webhook_url', 
                'name': 'Slack Webhook URL', 
                'value': '',
                'value_type': 'string',
                'description': 'Webhook URL for Slack notifications'
            },
            {
                'key': 'enable_slack_notifications', 
                'name': 'Enable Slack Notifications', 
                'value': 'false',
                'value_type': 'boolean',
                'description': 'Send system notifications to Slack'
            }
        ]
        
        for setting_data in default_settings:
            SettingsService.set_setting(
                key=setting_data['key'],
                value=setting_data['value'],
                value_type=setting_data['value_type'],
                name=setting_data['name'],
                description=setting_data['description'],
                group='integration'
            )
        
        # Refresh settings list
        settings_list = SettingsService.get_settings_by_group('integration')
    
    return render(request, 'settings/integration_settings.html', {
        'settings': settings_list,
        'current_group': 'integration'
    })

@login_required
@admin_required
def attendance_settings(request):
    """Attendance settings"""
    if request.method == 'POST':
        # Handle bulk update of settings
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                try:
                    setting = SystemSetting.objects.get(key=setting_key)
                    setting.value = value
                    setting.save()
                    
                    # Clear cache for this setting
                    SettingsService.delete_setting(setting_key)
                except SystemSetting.DoesNotExist:
                    continue
        
        messages.success(request, "Attendance settings updated successfully.")
        return redirect('attendance_settings')
    
    # Get attendance settings
    settings_list = SettingsService.get_settings_by_group('attendance')
    
    # Create default attendance settings if none exist
    if not settings_list.exists():
        default_settings = [
            {
                'key': 'working_days', 
                'name': 'Working Days', 
                'value': 'Monday,Tuesday,Wednesday,Thursday,Friday',
                'value_type': 'string',
                'description': 'Comma-separated list of working days'
            },
            {
                'key': 'work_start_time', 
                'name': 'Work Start Time', 
                'value': '09:00',
                'value_type': 'string',
                'description': 'Default work start time (24-hour format)'
            },
            {
                'key': 'work_end_time', 
                'name': 'Work End Time', 
                'value': '17:00',
                'value_type': 'string',
                'description': 'Default work end time (24-hour format)'
            },
            {
                'key': 'grace_period_minutes', 
                'name': 'Grace Period (Minutes)', 
                'value': '15',
                'value_type': 'integer',
                'description': 'Grace period in minutes for late arrivals'
            },
            {
                'key': 'overtime_threshold_hours', 
                'name': 'Overtime Threshold (Hours)', 
                'value': '8',
                'value_type': 'integer',
                'description': 'Hours per day before overtime is calculated'
            },
            {
                'key': 'enable_geofencing', 
                'name': 'Enable Geofencing', 
                'value': 'false',
                'value_type': 'boolean',
                'description': 'Restrict check-in to specific locations'
            },
            {
                'key': 'office_coordinates', 
                'name': 'Office Coordinates', 
                'value': '0,0',
                'value_type': 'string',
                'description': 'Latitude,Longitude of office location'
            },
            {
                'key': 'geofence_radius_meters', 
                'name': 'Geofence Radius (Meters)', 
                'value': '100',
                'value_type': 'integer',
                'description': 'Radius in meters for geofence check-in'
            }
        ]
        
        for setting_data in default_settings:
            SettingsService.set_setting(
                key=setting_data['key'],
                value=setting_data['value'],
                value_type=setting_data['value_type'],
                name=setting_data['name'],
                description=setting_data['description'],
                group='attendance'
            )
        
        # Refresh settings list
        settings_list = SettingsService.get_settings_by_group('attendance')
    
    return render(request, 'settings/attendance_settings.html', {
        'settings': settings_list,
        'current_group': 'attendance'
    })

@login_required
@admin_required
def leave_settings(request):
    """Leave settings"""
    if request.method == 'POST':
        # Handle bulk update of settings
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                try:
                    setting = SystemSetting.objects.get(key=setting_key)
                    setting.value = value
                    setting.save()
                    
                    # Clear cache for this setting
                    SettingsService.delete_setting(setting_key)
                except SystemSetting.DoesNotExist:
                    continue
        
        messages.success(request, "Leave settings updated successfully.")
        return redirect('leave_settings')
    
    # Get leave settings
    settings_list = SettingsService.get_settings_by_group('leave')
    
    # Create default leave settings if none exist
    if not settings_list.exists():
        default_settings = [
            {
                'key': 'annual_leave_days', 
                'name': 'Annual Leave Days', 
                'value': '20',
                'value_type': 'integer',
                'description': 'Default annual leave days per year'
            },
            {
                'key': 'sick_leave_days', 
                'name': 'Sick Leave Days', 
                'value': '10',
                'value_type': 'integer',
                'description': 'Default sick leave days per year'
            },
            {
                'key': 'enable_leave_accrual', 
                'name': 'Enable Leave Accrual', 
                'value': 'true',
                'value_type': 'boolean',
                'description': 'Enable gradual leave accrual throughout the year'
            },
            {
                'key': 'leave_carryover_limit', 
                'name': 'Leave Carryover Limit', 
                'value': '5',
                'value_type': 'integer',
                'description': 'Maximum days that can be carried over to next year'
            },
            {
                'key': 'require_leave_attachment', 
                'name': 'Require Leave Attachments', 
                'value': 'false',
                'value_type': 'boolean',
                'description': 'Require attachments (e.g., medical certificates) for leave requests'
            },
            {
                'key': 'min_days_before_leave', 
                'name': 'Minimum Days Before Leave', 
                'value': '3',
                'value_type': 'integer',
                'description': 'Minimum days in advance to request leave'
            },
            {
                'key': 'leave_types', 
                'name': 'Leave Types', 
                'value': 'Annual Leave,Sick Leave,Maternity Leave,Paternity Leave,Personal Leave,Bereavement Leave,Unpaid Leave',
                'value_type': 'string',
                'description': 'Comma-separated list of available leave types'
            }
        ]
        
        for setting_data in default_settings:
            SettingsService.set_setting(
                key=setting_data['key'],
                value=setting_data['value'],
                value_type=setting_data['value_type'],
                name=setting_data['name'],
                description=setting_data['description'],
                group='leave'
            )
        
        # Refresh settings list
        settings_list = SettingsService.get_settings_by_group('leave')
    
    return render(request, 'settings/leave_settings.html', {
        'settings': settings_list,
        'current_group': 'leave'
    })

@login_required
@admin_required
def performance_settings(request):
    """Performance settings"""
    if request.method == 'POST':
        # Handle bulk update of settings
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                try:
                    setting = SystemSetting.objects.get(key=setting_key)
                    setting.value = value
                    setting.save()
                    
                    # Clear cache for this setting
                    SettingsService.delete_setting(setting_key)
                except SystemSetting.DoesNotExist:
                    continue
        
        messages.success(request, "Performance settings updated successfully.")
        return redirect('performance_settings')
    
    # Get performance settings
    settings_list = SettingsService.get_settings_by_group('performance')
    
    # Create default performance settings if none exist
    if not settings_list.exists():
        default_settings = [
            {
                'key': 'performance_review_frequency', 
                'name': 'Performance Review Frequency', 
                'value': 'Quarterly',
                'value_type': 'string',
                'description': 'Frequency of performance reviews (Monthly, Quarterly, Semi-Annually, Annually)'
            },
            {
                'key': 'enable_self_assessment', 
                'name': 'Enable Self Assessment', 
                'value': 'true',
                'value_type': 'boolean',
                'description': 'Allow employees to submit self-assessments'
            },
            {
                'key': 'enable_peer_review', 
                'name': 'Enable Peer Review', 
                'value': 'true',
                'value_type': 'boolean',
                'description': 'Allow peer reviews for performance evaluation'
            },
            {
                'key': 'performance_rating_scale', 
                'name': 'Performance Rating Scale', 
                'value': '1,2,3,4,5',
                'value_type': 'string',
                'description': 'Comma-separated list of rating values'
            },
            {
                'key': 'performance_rating_labels', 
                'name': 'Performance Rating Labels', 
                'value': 'Unsatisfactory,Needs Improvement,Meets Expectations,Exceeds Expectations,Outstanding',
                'value_type': 'string',
                'description': 'Comma-separated labels for rating values'
            },
            {
                'key': 'enable_competency_assessment', 
                'name': 'Enable Competency Assessment', 
                'value': 'true',
                'value_type': 'boolean',
                'description': 'Include competency assessment in performance reviews'
            }
        ]
        
        for setting_data in default_settings:
            SettingsService.set_setting(
                key=setting_data['key'],
                value=setting_data['value'],
                value_type=setting_data['value_type'],
                name=setting_data['name'],
                description=setting_data['description'],
                group='performance'
            )
        
        # Refresh settings list
        settings_list = SettingsService.get_settings_by_group('performance')
    
    return render(request, 'settings/performance_settings.html', {
        'settings': settings_list,
        'current_group': 'performance'
    })

@login_required
@admin_required
def notification_settings(request):
    """Notification settings"""
    if request.method == 'POST':
        # Handle bulk update of settings
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                try:
                    setting = SystemSetting.objects.get(key=setting_key)
                    setting.value = value
                    setting.save()
                    
                    # Clear cache for this setting
                    SettingsService.delete_setting(setting_key)
                except SystemSetting.DoesNotExist:
                    continue
        
        messages.success(request, "Notification settings updated successfully.")
        return redirect('notification_settings')
    
    # Get notification settings
    settings_list = SettingsService.get_settings_by_group('notification')
    
    # Create default notification settings if none exist
    if not settings_list.exists():
        default_settings = [
            {
                'key': 'enable_email_notifications', 
                'name': 'Enable Email Notifications', 
                'value': 'true',
                'value_type': 'boolean',
                'description': 'Send system notifications via email'
            },
            {
                'key': 'enable_browser_notifications', 
                'name': 'Enable Browser Notifications', 
                'value': 'true',
                'value_type': 'boolean',
                'description': 'Enable browser push notifications'
            },
            {
                'key': 'enable_leave_request_notifications', 
                'name': 'Enable Leave Request Notifications', 
                'value': 'true',
                'value_type': 'boolean',
                'description': 'Send notifications for leave requests and approvals'
            },
            {
                'key': 'enable_birthday_notifications', 
                'name': 'Enable Birthday Notifications', 
                'value': 'true',
                'value_type': 'boolean',
                'description': 'Send notifications for employee birthdays'
            },
            {
                'key': 'enable_contract_expiry_notifications', 
                'name': 'Enable Contract Expiry Notifications', 
                'value': 'true',
                'value_type': 'boolean',
                'description': 'Send notifications for contract expirations'
            },
            {
                'key': 'days_before_contract_expiry_notification', 
                'name': 'Days Before Contract Expiry', 
                'value': '30',
                'value_type': 'integer',
                'description': 'Days before contract expiry to send notification'
            },
            {
                'key': 'notification_email_digests', 
                'name': 'Email Notification Digests', 
                'value': 'false',
                'value_type': 'boolean',
                'description': 'Send consolidated daily digests instead of individual emails'
            }
        ]
        
        for setting_data in default_settings:
            SettingsService.set_setting(
                key=setting_data['key'],
                value=setting_data['value'],
                value_type=setting_data['value_type'],
                name=setting_data['name'],
                description=setting_data['description'],
                group='notification'
            )
        
        # Refresh settings list
        settings_list = SettingsService.get_settings_by_group('notification')
    
    return render(request, 'settings/notification_settings.html', {
        'settings': settings_list,
        'current_group': 'notification'
    })

@login_required
@admin_required
def edit_setting(request, key):
    """Edit an individual setting"""
    try:
        setting = SystemSetting.objects.get(key=key)
    except SystemSetting.DoesNotExist:
        messages.error(request, f"Setting with key '{key}' not found.")
        return redirect('system_settings')
    
    if request.method == 'POST':
        form = SystemSettingForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()
            
            # Log the action
            AuditService.log_action(
                user=request.user,
                action='update',
                entity_type='system_setting',
                entity_id=key,
                description=f"Updated setting: {setting.name}",
                request=request
            )
            
            # Clear cache for this setting
            SettingsService.delete_setting(key)
            
            messages.success(request, "Setting updated successfully.")
            
            # Redirect back to appropriate settings page
            if setting.group == 'general':
                return redirect('general_settings')
            elif setting.group == 'appearance':
                return redirect('appearance_settings')
            elif setting.group == 'email':
                return redirect('email_settings')
            elif setting.group == 'security':
                return redirect('security_settings')
            elif setting.group == 'attendance':
                return redirect('attendance_settings')
            elif setting.group == 'leave':
                return redirect('leave_settings')
            elif setting.group == 'performance':
                return redirect('performance_settings')
            elif setting.group == 'notification':
                return redirect('notification_settings')
            elif setting.group == 'integration':
                return redirect('integration_settings')
            else:
                return redirect('system_settings')
    else:
        form = SystemSettingForm(instance=setting)
    
    return render(request, 'settings/edit_setting.html', {
        'form': form,
        'setting': setting
    })

@login_required
@admin_required
def create_setting(request):
    """Create a new setting"""
    if request.method == 'POST':
        form = SystemSettingForm(request.POST)
        if form.is_valid():
            setting = form.save()
            
            # Log the action
            AuditService.log_action(
                user=request.user,
                action='create',
                entity_type='system_setting',
                entity_id=setting.key,
                description=f"Created setting: {setting.name}",
                request=request
            )
            
            messages.success(request, "Setting created successfully.")
            
            # Redirect back to appropriate settings page
            if setting.group == 'general':
                return redirect('general_settings')
            elif setting.group == 'appearance':
                return redirect('appearance_settings')
            elif setting.group == 'email':
                return redirect('email_settings')
            elif setting.group == 'security':
                return redirect('security_settings')
            elif setting.group == 'attendance':
                return redirect('attendance_settings')
            elif setting.group == 'leave':
                return redirect('leave_settings')
            elif setting.group == 'performance':
                return redirect('performance_settings')
            elif setting.group == 'notification':
                return redirect('notification_settings')
            elif setting.group == 'integration':
                return redirect('integration_settings')
            else:
                return redirect('system_settings')
    else:
        # Get group from query parameter
        group = request.GET.get('group', 'general')
        form = SystemSettingForm(initial={'group': group})
    
    return render(request, 'settings/create_setting.html', {
        'form': form
    })

@login_required
@admin_required
def delete_setting(request, key):
    """Delete a setting"""
    try:
        setting = SystemSetting.objects.get(key=key)
    except SystemSetting.DoesNotExist:
        messages.error(request, f"Setting with key '{key}' not found.")
        return redirect('system_settings')
    
    if request.method == 'POST':
        group = setting.group
        
        # Log the action
        AuditService.log_action(
            user=request.user,
            action='delete',
            entity_type='system_setting',
            entity_id=key,
            description=f"Deleted setting: {setting.name}",
            request=request
        )
        
        # Delete the setting
        SettingsService.delete_setting(key)
        
        messages.success(request, "Setting deleted successfully.")
        
        # Redirect back to appropriate settings page
        if group == 'general':
            return redirect('general_settings')
        elif group == 'appearance':
            return redirect('appearance_settings')
        elif group == 'email':
            return redirect('email_settings')
        elif group == 'security':
            return redirect('security_settings')
        elif group == 'attendance':
            return redirect('attendance_settings')
        elif group == 'leave':
            return redirect('leave_settings')
        elif group == 'performance':
            return redirect('performance_settings')
        elif group == 'notification':
            return redirect('notification_settings')
        elif group == 'integration':
            return redirect('integration_settings')
        else:
            return redirect('system_settings')
    
    return render(request, 'settings/delete_setting.html', {
        'setting': setting
    })

@login_required
@admin_required
def audit_logs(request):
    """View system audit logs"""
    # Get filter parameters
    action_filter = request.GET.get('action', '')
    entity_filter = request.GET.get('entity_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    user_id = request.GET.get('user_id', '')
    
    # Base query
    logs = AuditLog.objects.all().select_related('user')
    
    # Apply filters
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if entity_filter:
        logs = logs.filter(entity_type=entity_filter)
    
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    
    if date_to:
        logs = logs.filter(timestamp__lte=date_to)
    
    if user_id:
        logs = logs.filter(user_id=user_id)
    
    # Order by most recent first
    logs = logs.order_by('-timestamp')
    
    # Get unique values for filters
    unique_actions = AuditLog.objects.values_list('action', flat=True).distinct()
    unique_entities = AuditLog.objects.values_list('entity_type', flat=True).distinct()
    
    return render(request, 'settings/audit_logs.html', {
        'logs': logs,
        'unique_actions': unique_actions,
        'unique_entities': unique_entities,
        'action_filter': action_filter,
        'entity_filter': entity_filter,
        'date_from': date_from,
        'date_to': date_to,
        'user_id': user_id
    })

@login_required
@admin_required
def user_audit_logs(request, user_id):
    """View audit logs for a specific user"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, f"User with ID {user_id} not found.")
        return redirect('audit_logs')
    
    logs = AuditLog.objects.filter(user=user).order_by('-timestamp')
    
    return render(request, 'settings/user_audit_logs.html', {
        'logs': logs,
        'user': user
    })

@login_required
@admin_required
def system_info(request):
    """View system information"""
    system_info = {
        'python_version': platform.python_version(),
        'django_version': django_settings.DJANGO_VERSION,
        'database_engine': django_settings.DATABASES['default']['ENGINE'],
        'os_info': f"{platform.system()} {platform.release()}",
        'hostname': platform.node(),
        'timezone': django_settings.TIME_ZONE,
        'debug_mode': 'Enabled' if django_settings.DEBUG else 'Disabled',
        'server_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z'),
    }
    
    # Get database stats
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM django_migrations")
            migrations_count = cursor.fetchone()[0]
            system_info['migrations_count'] = migrations_count
    except:
        system_info['migrations_count'] = 'N/A'
    
    # Get model counts
    model_counts = []
    from django.apps import apps
    for app_config in apps.get_app_configs():
        if app_config.name.startswith('django.') or app_config.name == 'rest_framework':
            continue  # Skip Django's internal apps
        
        app_models = {}
        for model in app_config.get_models():
            try:
                count = model.objects.count()
                app_models[model.__name__] = count
            except:
                app_models[model.__name__] = 'Error'
        
        if app_models:
            model_counts.append({
                'app_name': app_config.verbose_name,
                'models': app_models
            })
    
    return render(request, 'settings/system_info.html', {
        'system_info': system_info,
        'model_counts': model_counts
    })

@login_required
@admin_required
def test_email(request):
    """Test email configuration"""
    if request.method == 'POST':
        recipient = request.POST.get('recipient')
        subject = request.POST.get('subject', 'HRMS Test Email')
        message = request.POST.get('message', 'This is a test email from the HRMS system.')
        
        if not recipient:
            messages.error(request, "Recipient email is required.")
            return redirect('test_email')
        
        # Get email settings from database or use Django defaults
        email_host = SettingsService.get_setting('email_host', django_settings.EMAIL_HOST)
        email_port = SettingsService.get_setting('email_port', django_settings.EMAIL_PORT)
        email_use_tls = SettingsService.get_setting('email_use_tls', django_settings.EMAIL_USE_TLS)
        email_host_user = SettingsService.get_setting('email_host_user', django_settings.EMAIL_HOST_USER)
        email_host_password = SettingsService.get_setting('email_host_password', django_settings.EMAIL_HOST_PASSWORD)
        default_from_email = SettingsService.get_setting('default_from_email', django_settings.DEFAULT_FROM_EMAIL)
        
        # Temporarily override email settings
        django_settings.EMAIL_HOST = email_host
        django_settings.EMAIL_PORT = int(email_port) if isinstance(email_port, str) else email_port
        django_settings.EMAIL_USE_TLS = email_use_tls
        django_settings.EMAIL_HOST_USER = email_host_user
        django_settings.EMAIL_HOST_PASSWORD = email_host_password
        django_settings.DEFAULT_FROM_EMAIL = default_from_email
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=default_from_email,
                recipient_list=[recipient],
                fail_silently=False
            )
            
            # Log the action
            AuditService.log_action(
                user=request.user,
                action='other',
                entity_type='email',
                description=f"Sent test email to {recipient}",
                request=request
            )
            
            messages.success(request, f"Test email sent to {recipient} successfully.")
        except Exception as e:
            messages.error(request, f"Failed to send test email: {str(e)}")
        
        return redirect('email_settings')
    
    return render(request, 'settings/test_email.html')