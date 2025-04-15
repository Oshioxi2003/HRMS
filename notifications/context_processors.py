from .models import Notification

def notification_processor(request):
    context = {
        'unread_notification_count': 0,
        'recent_notifications': []
    }
    
    if request.user.is_authenticated:
        context['unread_notification_count'] = Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).count()
        
        context['recent_notifications'] = Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).order_by('-created_date')[:5]
    
    return context
