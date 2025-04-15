from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.contrib.auth import get_user_model
from .models import Permission
from .forms import CustomUserCreationForm, CustomUserChangeForm, PermissionForm
from .decorators import admin_required
from django.db.models import Q

User = get_user_model()

@login_required
@admin_required
def admin_dashboard(request):
    """Dashboard for admin users"""
    # User statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    
    # User by role statistics
    user_by_role = User.objects.values('role').annotate(count=Count('id'))
    
    # Recent users
    recent_users = User.objects.order_by('-date_joined')[:5]
    
    # Permission statistics
    permission_by_module = Permission.objects.values('module').annotate(count=Count('permission_id'))
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'user_by_role': user_by_role,
        'recent_users': recent_users,
        'permission_by_module': permission_by_module
    }
    return render(request, 'accounts/admin_dashboard.html', context)

@login_required
@admin_required
def user_list(request):
    """List all users in the system"""
    query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    users = User.objects.all().order_by('-date_joined')
    
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    if status_filter:
        if status_filter == 'Active':
            users = users.filter(is_active=True)
        else:
            users = users.filter(is_active=False)
    
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'accounts/user_list.html', {
        'page_obj': page_obj,
        'query': query,
        'role_filter': role_filter,
        'status_filter': status_filter
    })

@login_required
@admin_required
def user_create(request):
    """Create a new user"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'User created successfully')
            return redirect('user_detail', pk=user.pk)
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/user_form.html', {'form': form})