from .models import SystemLog
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext as _

class SystemLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Log only POST/PUT/DELETE actions by authenticated users
        if request.method in ['POST', 'PUT', 'DELETE'] and request.user.is_authenticated:
            # Exclude some paths like admin actions, static files, etc.
            excluded_paths = ['/admin/jsi18n/', '/static/', '/media/']
            if not any(request.path.startswith(path) for path in excluded_paths):
                SystemLog.objects.create(
                    user=request.user,
                    action=f"{request.method} {request.path}",
                    details=request.POST.get('action', ''),
                    ip=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
        
        return response
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class EmployeeApprovalMiddleware(MiddlewareMixin):
    """Middleware to check if employee is approved before allowing access"""
    
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None
            
        # URLs that are always accessible, even for unapproved employees
        exempt_urls = [
            reverse('logout'),
            reverse('password_reset'),
            reverse('approval_pending'),
            '/admin/',  # Admin URLs
            '/static/',  # Static files
            '/media/',   # Media files
        ]
        
        # Check if current URL is exempt
        current_path = request.path
        if any(current_path.startswith(url) for url in exempt_urls):
            return None
        
        # Exempt users with Admin, HR, or Manager roles
        if request.user.role in ['Admin', 'HR', 'Manager'] or request.user.is_staff or request.user.is_superuser:
            return None
            
        # Check if user has an employee profile
        if not hasattr(request.user, 'employee') or request.user.employee is None:
            # Users without employee profiles can access certain areas
            return None
            
        # Only check approval status for regular employees
        if request.user.employee.approval_status != 'Approved':
            messages.warning(request, _('Your employee profile is pending approval. Please wait for an administrator to approve your account.'))
            return redirect('approval_pending')
        
        return None