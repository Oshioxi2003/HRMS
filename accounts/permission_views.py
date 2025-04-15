from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.contrib.auth import get_user_model
from .models import Permission
from .forms import CustomUserCreationForm, CustomUserChangeForm, PermissionForm
from .decorators import admin_required


@login_required
@admin_required
def permission_list(request):
    """List all permissions in the system"""
    permissions = Permission.objects.all().order_by('role', 'module')
    
    # Filter by role and module
    role_filter = request.GET.get('role', '')
    module_filter = request.GET.get('module', '')
    
    if role_filter:
        permissions = permissions.filter(role=role_filter)
    
    if module_filter:
        permissions = permissions.filter(module=module_filter)
    
    # Get unique modules for filter dropdown
    modules = Permission.objects.values_list('module', flat=True).distinct()
    
    paginator = Paginator(permissions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'accounts/permission_list.html', {
        'page_obj': page_obj,
        'role_filter': role_filter,
        'module_filter': module_filter,
        'modules': modules
    })

@login_required
@admin_required
def permission_create(request):
    """Create a new permission"""
    if request.method == 'POST':
        form = PermissionForm(request.POST)
        if form.is_valid():
            # Check if permission already exists
            role = form.cleaned_data['role']
            module = form.cleaned_data['module']
            
            if Permission.objects.filter(role=role, module=module).exists():
                messages.error(request, f'Permission for {role} on {module} already exists')
                return render(request, 'accounts/permission_form.html', {'form': form})
            
            permission = form.save()
            messages.success(request, 'Permission created successfully')
            return redirect('permission_list')
    else:
        form = PermissionForm()
    
    return render(request, 'accounts/permission_form.html', {'form': form})