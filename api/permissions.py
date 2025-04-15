from rest_framework import permissions

class IsOwnerOrHR(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or HR personnel to access it.
    
    This permission is designed for models that have an employee field and 
    is used for objects related to employees like attendance, leave requests, etc.
    """
    
    def has_object_permission(self, request, view, obj):
        # HR and Admins always have permission
        if request.user.role in ['HR', 'Admin']:
            return True
        
        # Check if object has employee attribute and if it matches the request user's employee
        if hasattr(obj, 'employee') and obj.employee:
            return obj.employee == request.user.employee
        
        return False
    
    def has_permission(self, request, view):
        # Allow list view for HR and Admin
        if request.method in permissions.SAFE_METHODS and request.user.role in ['HR', 'Admin']:
            return True
        
        # For other methods or non-HR/Admin, will check at object level
        return request.user.is_authenticated

class IsManager(permissions.BasePermission):
    """
    Custom permission to only allow managers or higher to access a resource.
    
    For department-specific objects, checks if user is manager of that department.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated and has appropriate role
        if not request.user.is_authenticated:
            return False
        
        return request.user.role in ['Manager', 'HR', 'Admin']
    
    def has_object_permission(self, request, view, obj):
        # HR and Admins always have permission
        if request.user.role in ['HR', 'Admin']:
            return True
        
        # Managers can only access objects related to their department
        if request.user.role == 'Manager':
            # Check if user has employee profile and department
            if not (request.user.employee and request.user.employee.department):
                return False
            
            # Check if object has department or employee with department
            if hasattr(obj, 'department') and obj.department:
                return obj.department == request.user.employee.department
            
            if hasattr(obj, 'employee') and obj.employee and obj.employee.department:
                return obj.employee.department == request.user.employee.department
        
        return False

class IsEmployeeOwner(permissions.BasePermission):
    """
    Custom permission to only allow users to access their own employee data.
    
    Also allows managers to access data for employees in their department,
    and HR/Admin to access all employee data.
    """
    
    def has_permission(self, request, view):
        # Anyone can list/view, specific permissions checked at object level
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # For create/update/delete, check role
        return request.user.is_authenticated and (
            request.user.role in ['HR', 'Admin'] or 
            (hasattr(request.user, 'employee') and request.user.employee is not None)
        )
    
    def has_object_permission(self, request, view, obj):
        # HR and Admins always have permission
        if request.user.role in ['HR', 'Admin']:
            return True
        
        # Regular employees can only access their own data
        if hasattr(request.user, 'employee') and request.user.employee:
            if obj == request.user.employee:
                return True
            
            # For related objects (like leave requests)
            if hasattr(obj, 'employee') and obj.employee == request.user.employee:
                return True
        
        # Managers can access data for employees in their department
        if (request.user.role == 'Manager' and 
            request.user.employee and 
            request.user.employee.department):
            
            # Check if object is an employee or has employee attribute
            target_employee = obj if hasattr(obj, 'department') else getattr(obj, 'employee', None)
            
            if target_employee and target_employee.department:
                return target_employee.department == request.user.employee.department
        
        return False