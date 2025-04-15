from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from .models import OnboardingTask, EmployeeOnboarding, EmployeeTaskStatus
from .forms import OnboardingTaskForm, EmployeeOnboardingForm, TaskStatusUpdateForm
from employee.models import Employee
from accounts.decorators import hr_required, check_module_permission
from notifications.services import create_notification
from accounts.models import *
@login_required
@hr_required
def onboarding_list(request):
    """Hiển thị danh sách tất cả các quy trình onboarding"""
    onboardings = EmployeeOnboarding.objects.all().order_by('-start_date')
    return render(request, 'onboarding/onboarding_list.html', {'onboardings': onboardings})

@login_required
@hr_required
def onboarding_task_create(request):
    """Tạo một nhiệm vụ onboarding mới"""
    if request.method == 'POST':
        form = OnboardingTaskForm(request.POST)
        if form.is_valid():
            task = form.save()
            messages.success(request, 'Nhiệm vụ onboarding đã được tạo thành công.')
            return redirect('onboarding_task_list')
    else:
        form = OnboardingTaskForm()
    
    return render(request, 'onboarding/onboarding_task_form.html', {'form': form, 'action': 'Create'})

@login_required
def manager_onboarding_tasks(request, employee_id):
    """Hiển thị và quản lý các nhiệm vụ onboarding của quản lý cho một nhân viên cụ thể"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    # Kiểm tra xem người quản lý có quyền xem nhiệm vụ của nhân viên này không
    if request.user.employee.department != employee.department:
        messages.error(request, "Bạn không có quyền xem nhiệm vụ onboarding của nhân viên này.")
        return redirect('dashboard')
    
    try:
        onboarding = EmployeeOnboarding.objects.get(employee=employee)
    except EmployeeOnboarding.DoesNotExist:
        messages.warning(request, 'Không tìm thấy quy trình onboarding cho nhân viên này.')
        return redirect('employee_detail', pk=employee_id)
    
    task_statuses = EmployeeTaskStatus.objects.filter(
        onboarding=onboarding,
        task__responsible_role='Manager'
    ).select_related('task')
    
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        new_status = request.POST.get('status')
        comments = request.POST.get('comments')
        
        task_status = get_object_or_404(EmployeeTaskStatus, pk=task_id, onboarding=onboarding)
        task_status.status = new_status
        task_status.comments = comments
        task_status.save()
        
        messages.success(request, 'Trạng thái nhiệm vụ đã được cập nhật.')
        return redirect('manager_onboarding_tasks', employee_id=employee_id)
    
    return render(request, 'onboarding/manager_tasks.html', {
        'employee': employee,
        'onboarding': onboarding,
        'task_statuses': task_statuses
    })

@login_required
@hr_required
def create_employee_onboarding(request, employee_id):
    """Start onboarding process for a new employee"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    # Check if onboarding already exists
    if EmployeeOnboarding.objects.filter(employee=employee).exists():
        messages.warning(request, 'Onboarding process already exists for this employee')
        return redirect('employee_onboarding_detail', employee_id=employee_id)
    
    if request.method == 'POST':
        form = EmployeeOnboardingForm(request.POST)
        if form.is_valid():
            onboarding = form.save(commit=False)
            onboarding.employee = employee
            onboarding.created_by = request.user
            onboarding.status = 'In Progress'
            onboarding.save()
            
            # Automatically add appropriate tasks based on department, position, etc.
            tasks = OnboardingTask.objects.filter(
                Q(department_specific=False, position_specific=False) |
                (Q(department_specific=True) & Q(department=employee.department)) |
                (Q(position_specific=True) & Q(position=employee.position))
            )
            
            for task in tasks:
                EmployeeTaskStatus.objects.create(
                    onboarding=onboarding,
                    task=task,
                    status='Not Started'
                )
            
            # Send notifications to appropriate users
            if employee.department:
                # Find department manager
                manager = Employee.objects.filter(
                    department=employee.department,
                    position__position_name__icontains='manager'
                ).first()
                
                if manager:
                    manager_user = User.objects.filter(employee=manager).first()
                    if manager_user:
                        create_notification(
                            user=manager_user,
                            notification_type='System',
                            title='New Employee Onboarding',
                            message=f'Onboarding process has started for {employee.full_name}. Please complete your assigned tasks.',
                            link=f'/onboarding/{employee_id}/manager-tasks/'
                        )
            
            messages.success(request, 'Onboarding process created successfully')
            return redirect('employee_onboarding_detail', employee_id=employee_id)
    
    else:
        # Set default dates
        today = timezone.now().date()
        target_date = today + timedelta(days=30)  # Default 30 days for onboarding
        form = EmployeeOnboardingForm(initial={
            'start_date': today,
            'target_completion_date': target_date
        })
    
    return render(request, 'onboarding/create_onboarding.html', {
        'form': form,
        'employee': employee
    })

@login_required
@check_module_permission('onboarding', 'View')
def employee_onboarding_detail(request, employee_id):
    """View onboarding details for an employee"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    try:
        onboarding = EmployeeOnboarding.objects.get(employee=employee)
    except EmployeeOnboarding.DoesNotExist:
        messages.warning(request, 'No onboarding process found for this employee')
        if request.user.role in ['HR', 'Admin']:
            return redirect('create_employee_onboarding', employee_id=employee_id)
        return redirect('employee_detail', pk=employee_id)
    
    # Get task statuses
    task_statuses = EmployeeTaskStatus.objects.filter(onboarding=onboarding).select_related('task')
    
    # Calculate progress percentage
    total_tasks = task_statuses.count()
    completed_tasks = task_statuses.filter(status='Completed').count()
    progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    # Group tasks by responsible role
    hr_tasks = task_statuses.filter(task__responsible_role='HR')
    manager_tasks = task_statuses.filter(task__responsible_role='Manager')
    it_tasks = task_statuses.filter(task__responsible_role='IT')
    employee_tasks = task_statuses.filter(task__responsible_role='Employee')
    admin_tasks = task_statuses.filter(task__responsible_role='Admin')
    
    # Check if current user can update tasks
    can_update_hr = request.user.role in ['HR', 'Admin']
    can_update_manager = (request.user.role == 'Manager' and request.user.employee and
                          request.user.employee.department == employee.department)
    can_update_admin = request.user.role == 'Admin'
    can_update_employee = (request.user.employee == employee)
    
    # Determine which tasks the current user can update
    for task_status in task_statuses:
        role = task_status.task.responsible_role
        
        if role == 'HR' and can_update_hr:
            task_status.can_update = True
        elif role == 'Manager' and can_update_manager:
            task_status.can_update = True
        elif role == 'Admin' and can_update_admin:
            task_status.can_update = True
        elif role == 'Employee' and can_update_employee:
            task_status.can_update = True
        elif role == 'IT' and request.user.role == 'Admin':  # Only admin can update IT tasks in this example
            task_status.can_update = True
        else:
            task_status.can_update = False
    
    return render(request, 'onboarding/onboarding_detail.html', {
        'employee': employee,
        'onboarding': onboarding,
        'task_statuses': task_statuses,
        'progress_percentage': progress_percentage,
        'hr_tasks': hr_tasks,
        'manager_tasks': manager_tasks,
        'it_tasks': it_tasks,
        'employee_tasks': employee_tasks,
        'admin_tasks': admin_tasks,
        'can_update_hr': can_update_hr,
        'can_update_manager': can_update_manager,
        'can_update_admin': can_update_admin,
        'can_update_employee': can_update_employee
    })

@login_required
def update_task_status(request, task_status_id):
    """Update the status of an onboarding task"""
    task_status = get_object_or_404(EmployeeTaskStatus, pk=task_status_id)
    
    # Check if user has permission to update this task
    has_permission = False
    role = task_status.task.responsible_role
    
    if role == 'HR' and request.user.role in ['HR', 'Admin']:
        has_permission = True
    elif role == 'Manager' and request.user.role in ['Manager', 'HR', 'Admin']:
        if request.user.employee and task_status.onboarding.employee.department:
            if request.user.employee.department == task_status.onboarding.employee.department:
                has_permission = True
    elif role == 'Admin' and request.user.role == 'Admin':
        has_permission = True
    elif role == 'Employee' and request.user.employee == task_status.onboarding.employee:
        has_permission = True
    elif role == 'IT' and request.user.role == 'Admin':  # Only admin can update IT tasks in this example
        has_permission = True
    
    if not has_permission:
        messages.error(request, "You don't have permission to update this task.")
        return redirect('employee_onboarding_detail', employee_id=task_status.onboarding.employee.employee_id)
    
    if request.method == 'POST':
        form = TaskStatusUpdateForm(request.POST, instance=task_status)
        if form.is_valid():
            status = form.save(commit=False)
            
            # If marking as completed, set completion date and completed_by
            if status.status == 'Completed' and not status.completion_date:
                status.completion_date = timezone.now().date()
                status.completed_by = request.user
            
            status.save()
            
            # Check if all tasks are completed
            onboarding = task_status.onboarding
            all_completed = EmployeeTaskStatus.objects.filter(onboarding=onboarding).exclude(status='Completed').count() == 0
            
            if all_completed and onboarding.status != 'Completed':
                onboarding.status = 'Completed'
                onboarding.actual_completion_date = timezone.now().date()
                onboarding.save()
                
                # Notify HR about completed onboarding
                from notifications.services import notify_hr_staff
                notify_hr_staff(
                    notification_type='System',
                    title='Onboarding Completed',
                    message=f'Onboarding process for {onboarding.employee.full_name} has been completed.',
                    link=f'/onboarding/{onboarding.employee.employee_id}/detail/'
                )
            
            messages.success(request, 'Task status updated successfully.')
            return redirect('employee_onboarding_detail', employee_id=task_status.onboarding.employee.employee_id)
    else:
        form = TaskStatusUpdateForm(instance=task_status)
    
    return render(request, 'onboarding/update_task_status.html', {
        'form': form,
        'task_status': task_status
    })


@login_required
def onboarding_task_list(request):
    """List all onboarding tasks"""
    tasks = OnboardingTask.objects.all().order_by('task_name')
    
    return render(request, 'onboarding/onboarding_task_list.html', {'tasks': tasks})

@login_required
def onboarding_task_edit(request, task_id):
    """Edit an onboarding task"""
    task = get_object_or_404(OnboardingTask, task_id=task_id)
    
    if request.method == 'POST':
        form = OnboardingTaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Onboarding task updated successfully')
            return redirect('onboarding_task_list')
    else:
        form = OnboardingTaskForm(instance=task)
    
    return render(request, 'onboarding/task_form.html', {'form': form})

@login_required
def onboarding_task_delete(request, task_id):
    """Delete an onboarding task"""
    task = get_object_or_404(OnboardingTask, task_id=task_id)
    
    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Onboarding task deleted successfully')
        return redirect('onboarding_task_list')
    
    return render(request, 'onboarding/task_delete_confirm.html', {'task': task})

@login_required
@hr_required
def my_onboarding(request):
    """View the onboarding tasks for the logged-in employee"""
    if not request.user.employee:
        messages.error(request, "You don't have an employee profile.")
        return redirect('dashboard')
    
    try:
        onboarding = EmployeeOnboarding.objects.get(employee=request.user.employee)
    except EmployeeOnboarding.DoesNotExist:
        messages.warning(request, 'No onboarding process found for your profile.')
        return redirect('employee_detail', pk=request.user.employee.employee_id)
    
    task_statuses = EmployeeTaskStatus.objects.filter(onboarding=onboarding).select_related('task')
    
    return render(request, 'onboarding/my_onboarding.html', {
        'employee': request.user.employee,
        'onboarding': onboarding,
        'task_statuses': task_statuses
    })
