from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Notification

@login_required
def notification_list(request):
    """View all notifications"""
    notifications = Notification.objects.filter(user=request.user)
    
    # Filter by type
    notification_type = request.GET.get('type', '')
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    # Filter by read status
    read_status = request.GET.get('read', '')
    if read_status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif read_status == 'read':
        notifications = notifications.filter(is_read=True)
    
    paginator = Paginator(notifications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'notifications/notification_list.html', {
        'page_obj': page_obj,
        'notification_type': notification_type,
        'read_status': read_status,
        'unread_count': Notification.objects.filter(user=request.user, is_read=False).count()
    })

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, notification_id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    # Check if request wants JSON response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    # Redirect to notification detail or list
    redirect_url = request.POST.get('next', 'notification_list')
    return redirect(redirect_url)

@login_required
@require_POST
def mark_all_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    # Check if request wants JSON response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('notification_list')

@login_required
def get_unread_notification_count(request):
    """API endpoint to get unread notification count"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})

@login_required
def get_recent_notifications(request):
    """API endpoint to get recent notifications"""
    notifications = Notification.objects.filter(user=request.user, is_read=False)[:5]
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.notification_id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message[:100] + '...' if len(notification.message) > 100 else notification.message,
            'link': notification.link,
            'created_date': notification.created_date.strftime('%Y-%m-%d %H:%M')
        })
    
    return JsonResponse({
        'notifications': notifications_data,
        'total_unread': Notification.objects.filter(user=request.user, is_read=False).count()
    })


@login_required
def notification_list(request):
    """View all notifications"""
    notifications = Notification.objects.filter(user=request.user)
    
    # Get notification types for sidebar
    notification_types = Notification.NOTIFICATION_TYPES
    
    # Filter by type
    notification_type = request.GET.get('type', '')
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    # Filter by read status
    read_status = request.GET.get('read', '')
    if read_status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif read_status == 'read':
        notifications = notifications.filter(is_read=True)
    
    paginator = Paginator(notifications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'notifications/notification_list.html', {
        'page_obj': page_obj,
        'notification_type': notification_type,
        'read_status': read_status,
        'notification_types': notification_types,
        'unread_count': Notification.objects.filter(user=request.user, is_read=False).count()
    })

@login_required
def notification_detail(request, notification_id):
    """View notification details"""
    notification = get_object_or_404(Notification, notification_id=notification_id, user=request.user)
    
    # Get notification types for sidebar
    notification_types = Notification.NOTIFICATION_TYPES
    
    # Count unread notifications
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    return render(request, 'notifications/notification_detail.html', {
        'notification': notification,
        'notification_types': notification_types,
        'unread_count': unread_count
    })

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, notification_id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    # Check if request wants JSON response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    # Get next parameter or redirect to notification detail
    next_page = request.POST.get('next', '')
    if next_page:
        return redirect(next_page)
        
    # Redirect to notification detail or list
    if notification.link:
        return redirect(notification.link)
    else:
        return redirect('notification_detail', notification_id=notification_id)

@login_required
@require_POST
def mark_all_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    # Check if request wants JSON response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    messages.success(request, "All notifications marked as read.")
    return redirect('notification_list')

@login_required
def get_unread_notification_count(request):
    """API endpoint to get unread notification count"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})

@login_required
def get_recent_notifications(request):
    """API endpoint to get recent notifications"""
    notifications = Notification.objects.filter(user=request.user, is_read=False)[:5]
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.notification_id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message[:100] + '...' if len(notification.message) > 100 else notification.message,
            'link': notification.link,
            'created_date': notification.created_date.strftime('%Y-%m-%d %H:%M')
        })
    
    return JsonResponse({
        'notifications': notifications_data,
        'total_unread': Notification.objects.filter(user=request.user, is_read=False).count()
    })

@login_required
def notification_settings(request):
    """View and edit notification settings"""
    from django.conf import settings as django_settings
    import json
    
    # Get notification types for sidebar
    notification_types = Notification.NOTIFICATION_TYPES
    
    # Get user's notification settings from user profile or create default
    try:
        if hasattr(request.user, 'profile'):
            user_settings = json.loads(request.user.profile.notification_settings)
        else:
            # Default settings if user doesn't have profile or settings
            user_settings = {
                'system': {type_key: True for type_key, _ in notification_types},
                'email': {type_key: type_key in ['Leave', 'Salary', 'Performance'] for type_key, _ in notification_types},
                'frequency': 'daily'
            }
    except (AttributeError, json.JSONDecodeError):
        # Default settings if there's an error
        user_settings = {
            'system': {type_key: True for type_key, _ in notification_types},
            'email': {type_key: type_key in ['Leave', 'Salary', 'Performance'] for type_key, _ in notification_types},
            'frequency': 'daily'
        }
    
    if request.method == 'POST':
        # Extract settings from form
        updated_settings = {
            'system': {},
            'email': {},
            'frequency': request.POST.get('email_frequency', 'daily')
        }
        
        # Process system notifications
        for type_key, _ in notification_types:
            updated_settings['system'][type_key] = f'system_{type_key}' in request.POST
            updated_settings['email'][type_key] = f'email_{type_key}' in request.POST
        
        # Save settings to user profile
        if hasattr(request.user, 'profile'):
            request.user.profile.notification_settings = json.dumps(updated_settings)
            request.user.profile.save()
            messages.success(request, "Notification settings updated successfully.")
        else:
            # Create user profile if it doesn't exist
            try:
                from employee.models import UserProfile
                profile = UserProfile.objects.create(
                    user=request.user,
                    notification_settings=json.dumps(updated_settings)
                )
                messages.success(request, "Notification settings updated successfully.")
            except ImportError:
                messages.error(request, "Could not save notification settings. User profile model not found.")
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return redirect('notification_settings')
    
    # Count unread notifications
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    return render(request, 'notifications/notification_settings.html', {
        'notification_types': notification_types,
        'settings': user_settings,
        'unread_count': unread_count
    })