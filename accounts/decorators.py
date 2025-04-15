from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.contrib import messages
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                raise PermissionDenied
        return _wrapped_view
    return decorator

def admin_required(view_func):
    return role_required(['Admin'])(view_func)

def hr_required(view_func):
    return role_required(['HR', 'Admin'])(view_func)

def manager_required(view_func):
    return role_required(['Manager', 'HR', 'Admin'])(view_func)

def employee_required(view_func):
    return role_required(['Employee', 'Manager', 'HR', 'Admin'])(view_func)

def check_module_permission(module, required_permission='View'):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Superusers have all permissions
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Special case for employee_evaluations - check if user is the employee being viewed
            if view_func.__name__ == 'employee_evaluations' and 'employee_id' in kwargs:
                employee_id = kwargs.get('employee_id')
                if request.user.employee and str(request.user.employee.employee_id) == str(employee_id):
                    return view_func(request, *args, **kwargs)
            
            # Admin and HR have all permissions by default
            if hasattr(request.user, 'role') and request.user.role in ['Admin', 'HR']:
                return view_func(request, *args, **kwargs)
            
            # For other roles, check permission directly based on user's groups and permissions
            if hasattr(request.user, 'role'):
                # For example: check if user has a permission like 'view_module'
                permission_codename = f"{required_permission.lower()}_{module.lower()}"
                if request.user.has_perm(f"accounts.{permission_codename}"):
                    return view_func(request, *args, **kwargs)
                
                # Add a message before denying permission
                messages.error(request, 
                    f"You don't have {required_permission} permission for the {module} module.")
            
            raise PermissionDenied
        return _wrapped_view
    return decorator

def employee_approved_required(view_func):
    """Check if user has an approved employee profile"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Admin and HR bypass this check
        if request.user.role in ['Admin', 'HR']:
            return view_func(request, *args, **kwargs)
            
        # Check if user has an employee profile
        if not hasattr(request.user, 'employee') or request.user.employee is None:
            messages.warning(request, "Bạn cần hoàn thiện hồ sơ nhân viên để truy cập tính năng này.")
            return redirect('employee_edit_profile')
            
        # Check if the employee profile is approved
        if request.user.employee.approval_status != 'Approved':
            messages.warning(request, "Hồ sơ nhân viên của bạn đang chờ phê duyệt. Vui lòng đợi quản trị viên phê duyệt.")
            return redirect('approval_pending')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view
