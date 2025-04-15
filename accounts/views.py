from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model, logout, update_session_auth_hash
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.views.generic import View
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone

from .forms import *
from accounts.decorators import hr_required, admin_required, manager_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission

User = get_user_model()

class ActivateAccountView(View):
    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        
        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.status = 'Active'
            user.save()
            messages.success(request, 'Tài khoản của bạn đã được xác nhận. Bạn có thể đăng nhập ngay bây giờ.')
            return redirect('login')
        else:
            messages.error(request, 'Liên kết kích hoạt không hợp lệ!')
            return redirect('register')
        
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                # Redirect based on user role
                if user.role == 'Admin':
                    return redirect('admin_dashboard')
                elif user.role == 'HR':
                    return redirect('hr_dashboard')
                elif user.role == 'Manager':
                    return redirect('manager_dashboard')
                else:
                    return redirect('employee_dashboard')
            else:
                messages.error(request, 'Tài khoản chưa được kích hoạt. Vui lòng kiểm tra email để kích hoạt.')
        else:
            # Check if user exists but might be using SSO
            try:
                user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
                if user.social_auth.exists():
                    messages.info(request, 'Tài khoản này sử dụng Google Sign-In. Vui lòng đăng nhập với Google.')
                else:
                    messages.error(request, 'Tên đăng nhập hoặc mật khẩu không chính xác.')
            except User.DoesNotExist:
                messages.error(request, 'Tên đăng nhập hoặc mật khẩu không chính xác.')
    
    return render(request, 'accounts/login.html')


@login_required
@hr_required
def user_management(request):
    """View for managing users"""
    users = User.objects.all().order_by('username')
    
    return render(request, 'accounts/user_management.html', {
        'users': users
    })

@login_required
@hr_required
def user_create(request):
    """Create a new user"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Tạo người dùng thành công.")
            return redirect('user_management')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'is_create': True
    })

@login_required
@hr_required
def user_update(request, user_id):
    """Update an existing user"""
    user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Cập nhật người dùng thành công.")
            return redirect('user_management')
    else:
        form = CustomUserChangeForm(instance=user)
    
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'is_create': False,
        'user': user
    })

@login_required
@hr_required
def user_delete(request, user_id):
    """Delete a user"""
    user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        user.delete()
        messages.success(request, "Xóa người dùng thành công.")
        return redirect('user_management')
    
    return render(request, 'accounts/user_confirm_delete.html', {
        'user': user
    })

def logout_view(request):
    """Log the user out and redirect to the login page"""
    logout(request)
    messages.success(request, 'Bạn đã đăng xuất thành công.')
    return redirect('login')


def register_view(request):
    """Function-based view for registration"""
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # If employee profile is created during registration and user has special role
            if hasattr(user, 'employee') and user.employee:
                if user.role in ['Admin', 'HR', 'Manager']:
                    user.employee.approval_status = 'Approved'
                    user.employee.approval_date = timezone.now()
                    user.employee.save()
            
            # Send success email
            current_site = get_current_site(request)
            mail_subject = 'Đăng Ký Tài Khoản HRMS Thành Công'
            message = render_to_string('accounts/email/account_activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'protocol': 'https' if request.is_secure() else 'http'
            })
            to_email = form.cleaned_data.get('email')
            email = EmailMessage(
                mail_subject, message, to=[to_email]
            )
            email.content_subtype = 'html'  # Send as HTML email
            email.send()
            
            # Log the user in immediately
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=user.username, password=raw_password)
            login(request, user)
            
            # Create system log entry
            from accounts.models import SystemLog
            SystemLog.objects.create(
                user=user,
                action="Registration",
                object_type="User",
                object_id=user.id,
                details="User registered successfully"
            )
            
            messages.success(request, 'Tài khoản của bạn đã được tạo thành công! Kiểm tra email để xem thông tin đăng nhập.')
            
            # Redirect to appropriate dashboard
            if user.role == 'Admin':
                return redirect('admin_dashboard')
            elif user.role == 'HR':
                return redirect('hr_dashboard')
            elif user.role == 'Manager':
                return redirect('manager_dashboard')
            else:
                return redirect('employee_dashboard')
    else:
        form = RegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def my_profile(request):
    """View user's own profile"""
    # Get recent activity
    activity_logs = SystemLog.objects.filter(user=request.user).order_by('-timestamp')[:10]
    
    return render(request, 'accounts/my_profile.html', {
        'activity_logs': activity_logs
    })

@login_required
def edit_profile(request):
    """Edit user's own profile"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hồ sơ cá nhân đã được cập nhật thành công')
            return redirect('my_profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/edit_profile.html', {'form': form})

@login_required
def change_password(request):
    """Change user's password"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = request.user
            if user.check_password(form.cleaned_data['current_password']):
                user.set_password(form.cleaned_data['new_password'])
                user.save()
                
                # Log the user back in
                update_session_auth_hash(request, user)
                
                messages.success(request, 'Đổi mật khẩu thành công')
                return redirect('my_profile')
            else:
                form.add_error('current_password', 'Mật khẩu không chính xác')
    else:
        form = PasswordChangeForm()
    
    return render(request, 'accounts/change_password.html', {'form': form})

@login_required
def system_logs(request):
    """View system logs (admin only)"""
    if request.user.role != 'Admin':
        messages.error(request, 'Bạn không có quyền truy cập trang này')
        return redirect('dashboard')
    
    # Get filters
    query = request.GET.get('q', '')
    user_filter = request.GET.get('user', '')
    action_filter = request.GET.get('action', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base query
    logs = SystemLog.objects.all().order_by('-timestamp')
    
    # Apply filters
    if query:
        logs = logs.filter(
            Q(details__icontains=query) |
            Q(action__icontains=query) |
            Q(object_type__icontains=query)
        )
    
    if user_filter:
        logs = logs.filter(user_id=user_filter)
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)
    
    # Pagination
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    logs_page = paginator.get_page(page_number)
    
    # Get unique users and actions for filter dropdowns
    users = User.objects.filter(id__in=SystemLog.objects.values_list('user', flat=True).distinct())
    actions = SystemLog.objects.values_list('action', flat=True).distinct()
    
    return render(request, 'accounts/system_logs.html', {
        'logs': logs_page,
        'query': query,
        'user_filter': user_filter,
        'action_filter': action_filter,
        'date_from': date_from,
        'date_to': date_to,
        'users': users,
        'actions': actions
    })

@login_required
@admin_required
def user_detail(request, user_id):
    """View details of a specific user"""
    user = get_object_or_404(User, pk=user_id)
    
    # Get user's role permissions using a different approach
    try:
        # Check if user has a role first
        if hasattr(user, 'role') and user.role:
            # Get permissions based on the user's groups and direct permissions
            permissions = user.user_permissions.all()
    except:
        permissions = []
    
    # Get user profile
    try:
        profile = user.profile
    except:
        profile = None
    
    # Get employee profile if exists
    try:
        employee = user.employee
    except:
        employee = None
    
    context = {
        'user_obj': user,
        'permissions': permissions,
        'profile': profile,
        'employee': employee,
    }
    
    return render(request, 'accounts/user_detail.html', context)

@login_required
@admin_required
def user_edit(request, user_id):
    """Edit a user's details"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật người dùng thành công')
            return redirect('user_detail', user_id=user.id)
    else:
        form = CustomUserChangeForm(instance=user)
    
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'user': user,
        'is_create': False
    })

@login_required
@admin_required
def user_activate(request, user_id):
    """Activate a user account"""
    user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST' or request.method == 'GET':
        user.is_active = True
        user.status = 'Active'
        user.save()
        
        # Log the activation
        SystemLog.objects.create(
            user=request.user,
            action='activate_user',
            object_type='User',
            object_id=user.id,
            details=f"Đã kích hoạt tài khoản người dùng: {user.username}"
        )
        
        messages.success(request, f'Người dùng {user.username} đã được kích hoạt thành công.')
        
        # Redirect back to the referring page or user list
        return redirect(request.META.get('HTTP_REFERER', 'user_list'))
    
    return render(request, 'accounts/user_confirm_action.html', {
        'user': user,
        'action': 'activate'
    })

@login_required
@admin_required
def user_deactivate(request, user_id):
    """Deactivate a user account"""
    user = get_object_or_404(User, pk=user_id)
    
    # Don't allow deactivating own account
    if user == request.user:
        messages.error(request, 'Bạn không thể vô hiệu hóa tài khoản của chính mình.')
        return redirect('user_list')
    
    if request.method == 'POST' or request.method == 'GET':
        user.is_active = False
        user.status = 'Locked'
        user.save()
        
        # Log the deactivation
        SystemLog.objects.create(
            user=request.user,
            action='deactivate_user',
            object_type='User',
            object_id=user.id,
            details=f"Đã vô hiệu hóa tài khoản người dùng: {user.username}"
        )
        
        messages.success(request, f'Người dùng {user.username} đã bị vô hiệu hóa thành công.')
        
        # Redirect back to the referring page or user list
        return redirect(request.META.get('HTTP_REFERER', 'user_list'))
    
    return render(request, 'accounts/user_confirm_action.html', {
        'user': user,
        'action': 'deactivate'
    })

@login_required
@admin_required
def permission_edit(request, permission_id):
    """Edit a permission"""
    permission = get_object_or_404(Permission, permission_id=permission_id)
    
    if request.method == 'POST':
        form = PermissionForm(request.POST, instance=permission)
        if form.is_valid():
            # Check if the new combination of role/module already exists
            role = form.cleaned_data['role']
            module = form.cleaned_data['module']
            
            if Permission.objects.filter(role=role, module=module).exclude(permission_id=permission_id).exists():
                messages.error(request, f'Quyền cho {role} trên {module} đã tồn tại')
            else:
                form.save()
                messages.success(request, 'Cập nhật quyền thành công')
                return redirect('permission_list')
    else:
        form = PermissionForm(instance=permission)
    
    return render(request, 'accounts/permission_form.html', {
        'form': form,
        'permission': permission,
        'is_edit': True
    })

@login_required
@admin_required
def permission_delete(request, permission_id):
    """Delete a permission"""
    if request.method == 'POST':
        permission = get_object_or_404(Permission, permission_id=permission_id)
        permission.delete()
        
        messages.success(request, 'Xóa quyền thành công')
        return redirect('permission_list')
    
    return redirect('permission_list')

def password_reset_request(request):
    """Handle password reset request"""
    if request.method == 'POST':
        email = request.POST.get('email', '')
        users = User.objects.filter(email=email)
        
        if users.exists():
            for user in users:
                # Generate reset token
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                
                # Send email
                current_site = get_current_site(request)
                mail_subject = 'Đặt lại mật khẩu HRMS của bạn'
                message = render_to_string('accounts/email/password_reset_email.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': uid,
                    'token': token,
                    'protocol': 'https' if request.is_secure() else 'http'
                })
                
                # Đảm bảo email được gửi dưới dạng HTML
                email_message = EmailMessage(
                    mail_subject, 
                    message, 
                    to=[user.email]
                )
                email_message.content_subtype = 'html'  # Quan trọng: Đặt content_subtype là 'html'
                email_message.send()
        
        # Always show success message to prevent email enumeration
        messages.success(request, 'Hướng dẫn đặt lại mật khẩu đã được gửi đến email của bạn nếu tài khoản tồn tại trong hệ thống.')
        return redirect('login')
    
    return render(request, 'accounts/password_reset.html')


def password_reset_confirm(request, uidb64, token):
    """Xác nhận đặt lại mật khẩu với token"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        validlink = user is not None and default_token_generator.check_token(user, token)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
        validlink = False
    
    if validlink:
        if request.method == 'POST':
            # Lấy mật khẩu mới từ form
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')
            
            # Kiểm tra mật khẩu trùng khớp
            if new_password1 != new_password2:
                messages.error(request, 'Mật khẩu không khớp.')
                return render(request, 'accounts/password_reset_confirm.html', {
                    'validlink': True,
                    'uidb64': uidb64,
                    'token': token
                })
            
            # Kiểm tra độ mạnh của mật khẩu
            if len(new_password1) < 8:
                messages.error(request, 'Mật khẩu phải có ít nhất 8 ký tự.')
                return render(request, 'accounts/password_reset_confirm.html', {
                    'validlink': True,
                    'uidb64': uidb64,
                    'token': token
                })
            
            if not any(char.isalpha() for char in new_password1):
                messages.error(request, 'Mật khẩu phải chứa ít nhất một chữ cái.')
                return render(request, 'accounts/password_reset_confirm.html', {
                    'validlink': True,
                    'uidb64': uidb64,
                    'token': token
                })
                
            if not any(char.isdigit() for char in new_password1):
                messages.error(request, 'Mật khẩu phải chứa ít nhất một chữ số.')
                return render(request, 'accounts/password_reset_confirm.html', {
                    'validlink': True,
                    'uidb64': uidb64,
                    'token': token
                })
            
            # Mật khẩu hợp lệ, tiến hành cập nhật
            user.set_password(new_password1)
            user.is_active = True
            user.status = 'Active'
            user.save()
            
            # Đăng nhập người dùng sau khi đặt lại mật khẩu
            user = authenticate(username=user.username, password=new_password1)
            if user:
                login(request, user)
            
            # Ghi log hoạt động
            from accounts.models import SystemLog
            SystemLog.objects.create(
                user=user,
                action="Đặt lại mật khẩu",
                object_type="User",
                object_id=user.id,
                details="Mật khẩu đã được đặt lại thành công thông qua email"
            )
            
            # Token tự động vô hiệu sau khi sử dụng thành công
            # (Django's PasswordResetTokenGenerator đảm bảo điều này)
            
            messages.success(request, 'Mật khẩu đã được đặt lại thành công. Bạn đã được đăng nhập.')
            
            # Chuyển hướng đến trang dashboard tương ứng
            if user.role == 'Admin':
                return redirect('admin_dashboard')
            elif user.role == 'HR':
                return redirect('hr_dashboard')
            elif user.role == 'Manager':
                return redirect('manager_dashboard')
            else:
                return redirect('employee_dashboard')
        
        # GET request - hiển thị form đặt lại mật khẩu
        return render(request, 'accounts/password_reset_confirm.html', {
            'validlink': True,
            'uidb64': uidb64,
            'token': token
        })
    else:
        # Link không hợp lệ hoặc đã hết hạn
        return render(request, 'accounts/password_reset_confirm.html', {
            'validlink': False
        })


def activate_account(request, uidb64, token):
    """Activate a user account with token"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.status = 'Active'
        user.save()
        messages.success(request, 'Tài khoản của bạn đã được kích hoạt. Bạn có thể đăng nhập ngay bây giờ.')
        return redirect('login')
    else:
        messages.error(request, 'Liên kết kích hoạt không hợp lệ hoặc đã hết hạn.')
        return redirect('register')


@login_required
def dashboard(request):
    """Main dashboard that redirects to appropriate role-based dashboard"""
    if not request.user.is_active:
        messages.error(request, 'Tài khoản của bạn chưa được kích hoạt')
        return redirect('login')
    
    # Redirect to appropriate dashboard based on user role
    if request.user.role == 'Admin':
        return redirect('admin_dashboard')
    elif request.user.role == 'HR':
        return redirect('hr_dashboard')
    elif request.user.role == 'Manager':
        return redirect('manager_dashboard')
    else:
        return redirect('employee_dashboard')

@login_required
def employee_dashboard(request):
    """Dashboard for regular employees"""
    if not request.user.employee:
        messages.info(request, 'Vui lòng hoàn thành hồ sơ nhân viên của bạn')
        return redirect('edit_profile')
    
    # Additional code for employee dashboard content would go here
    
    return render(request, 'dashboard/employee_dashboard.html')

@login_required
@manager_required
def manager_dashboard(request):
    """Dashboard for managers"""
    if not request.user.employee or not request.user.employee.department:
        messages.warning(request, 'Bạn chưa được phân công vào bộ phận nào')
        return redirect('employee_dashboard')
    
    # Additional code for manager dashboard content would go here
    
    return render(request, 'dashboard/manager_dashboard.html')

@login_required
@hr_required
def hr_dashboard(request):
    """Dashboard for HR personnel"""
    # Additional code for HR dashboard content would go here
    
    return render(request, 'dashboard/hr_dashboard.html')

@login_required
@admin_required
def admin_dashboard(request):
    """Dashboard for admin users with system metrics"""
    # User statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    
    user_by_role = User.objects.values('role').annotate(
        count=Count('id')
    ).order_by('role')
    
    # Recent user activity
    recent_logs = SystemLog.objects.all().order_by('-timestamp')[:10]
    
    # System health metrics (dummy data for example)
    system_health = {
        'database_size': '1.2 GB',
        'total_tables': '26',
        'total_records': User.objects.count(),
        'disk_usage': '45%',
        'memory_usage': '32%',
        'cpu_usage': '28%'
    }
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'user_by_role': user_by_role,
        'recent_logs': recent_logs,
        'system_health': system_health
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context)

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
def approval_pending(request):
    """Display a page informing the user that their account is pending approval"""
    # Check if user's employee profile is already approved
    if hasattr(request.user, 'employee') and request.user.employee.approval_status == 'Approved':
        messages.success(request, ('Tài khoản của bạn đã được phê duyệt. Chào mừng bạn đến với hệ thống!'))
        return redirect('dashboard')  # Redirect to main dashboard if already approved
        
    return render(request, 'accounts/approval_pending.html')
