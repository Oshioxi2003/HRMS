from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from .models import Notification
from employee.models import Employee
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json


User = get_user_model()

def create_notification(user, notification_type, title, message, link=None):
    """Create a new notification for a user"""
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )
    
    # Send real-time notification if channel layer is available
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            notification_data = {
                'id': notification.notification_id,
                'type': notification.notification_type,
                'title': notification.title,
                'message': notification.message,
                'link': notification.link,
                'created_date': notification.created_date.strftime('%Y-%m-%d %H:%M')
            }
            
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user.id}',
                {
                    'type': 'notification_message',
                    'notification': notification_data
                }
            )
    except:
        # Fallback to standard notification if real-time fails
        pass
    
    return notification

def notify_managers(department, notification_type, title, message, link=None):
    """Send notifications to all managers of a department"""
    # Get all users with Manager role in the department
    managers = User.objects.filter(
        role='Manager',
        employee__department=department,
        is_active=True
    )
    
    notifications = []
    for manager in managers:
        notifications.append(create_notification(
            user=manager,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link
        ))
    
    return notifications

def notify_hr_staff(notification_type, title, message, link=None):
    """Send notifications to all HR staff"""
    hr_users = User.objects.filter(role='HR', is_active=True)
    
    notifications = []
    for hr_user in hr_users:
        notifications.append(create_notification(
            user=hr_user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link
        ))
    
    return notifications

def notify_leave_request(leave_request):
    """Send notification about a leave request to managers"""
    employee = leave_request.employee
    department = employee.department
    
    if department:
        title = f"New Leave Request: {employee.full_name}"
        message = f"{employee.full_name} has requested {leave_request.leave_days} days of {leave_request.leave_type} from {leave_request.start_date} to {leave_request.end_date}."
        link = reverse('leave_approval', args=[leave_request.request_id])
        
        return notify_managers(department, 'Leave', title, message, link)
    
    return []

def notify_leave_status_update(leave_request):
    """Notify employee about leave request status update"""
    employee = leave_request.employee
    user = User.objects.filter(employee=employee).first()
    
    if user:
        title = f"Leave Request {leave_request.status}"
        message = f"Your leave request from {leave_request.start_date} to {leave_request.end_date} has been {leave_request.status.lower()}."
        if leave_request.approval_notes:
            message += f"\n\nNotes: {leave_request.approval_notes}"
        
        link = reverse('my_leave_requests')
        
        return create_notification(user, 'Leave', title, message, link)
    
    return None

def send_birthday_notifications():
    """Send birthday notifications for upcoming birthdays"""
    today = timezone.now().date()
    
    # Get employees with birthdays in the next 7 days
    employees_with_birthdays = []
    
    for i in range(7):
        check_date = today + timezone.timedelta(days=i)
        employees = Employee.objects.filter(
            date_of_birth__month=check_date.month,
            date_of_birth__day=check_date.day,
            status='Working'
        )
        
        for employee in employees:
            days_until = i
            employees_with_birthdays.append((employee, days_until))
    
    # Send notifications to HR and department managers
    for employee, days_until in employees_with_birthdays:
        if days_until == 0:
            title = f"Today is {employee.full_name}'s Birthday!"
            message = f"Today is {employee.full_name}'s birthday. Wish them a happy birthday!"
        else:
            title = f"Upcoming Birthday: {employee.full_name}"
            message = f"{employee.full_name}'s birthday is in {days_until} days on {today + timezone.timedelta(days=days_until)}."
        
        link = reverse('employee_detail', args=[employee.employee_id])
        
        # Notify HR
        notify_hr_staff('Birthday', title, message, link)
        
        # Notify department manager
        if employee.department:
            notify_managers(employee.department, 'Birthday', title, message, link)
    
    return len(employees_with_birthdays)