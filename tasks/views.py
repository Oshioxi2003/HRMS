from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from datetime import date, timedelta
from .models import TaskCategory, Task, TaskComment, TaskDependency
from .forms import *
from employee.models import Employee, Department
from accounts.decorators import *
from notifications.services import create_notification
from datetime import date, datetime


@login_required
@employee_approved_required
def my_tasks(request):
    """View tasks assigned to the employee"""
    if not request.user.employee:
        messages.error(request, "You don't have an employee profile.")
        return redirect('dashboard')
    
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    category_filter = request.GET.get('category', '')
    
    tasks = Task.objects.filter(assignee=request.user.employee)
    
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    
    if category_filter:
        tasks = tasks.filter(category_id=category_filter)
    
    # Default ordering: overdue first, then by due date
    tasks = tasks.order_by('-priority', 'due_date')
    
    # Categorize tasks
    overdue_tasks = [task for task in tasks if task.is_overdue()]
    today_tasks = [task for task in tasks if task.due_date == date.today() and task not in overdue_tasks]
    upcoming_tasks = [task for task in tasks if task.due_date > date.today() and task not in today_tasks]
    completed_tasks = [task for task in tasks if task.status == 'Completed']
    
    # Get task categories for filter
    categories = TaskCategory.objects.filter(is_active=True)
    
    return render(request, 'tasks/my_tasks.html', {
        'overdue_tasks': overdue_tasks,
        'today_tasks': today_tasks,
        'upcoming_tasks': upcoming_tasks,
        'completed_tasks': completed_tasks,
        'categories': categories,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'category_filter': category_filter
    })

@login_required
@manager_required
def create_task(request):
    """Create a new task"""
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES)
        if form.is_valid():
            task = form.save(commit=False)
            task.assigned_by = request.user
            
            # Set department from assignee
            if task.assignee and task.assignee.department:
                task.department = task.assignee.department
            
            task.save()
            
            # Send notification to assignee
            from django.contrib.auth import get_user_model
            User = get_user_model()
            assignee_user = User.objects.filter(employee=task.assignee).first()
            
            if assignee_user:
                create_notification(
                    user=assignee_user,
                    notification_type='Task',
                    title='New Task Assigned',
                    message=f'You have been assigned a new task: {task.title}',
                    link=f'/tasks/view/{task.task_id}/'
                )
            
            messages.success(request, "Task created successfully.")
            
            # Check if dependencies need to be added
            if 'add_dependencies' in request.POST:
                return redirect('add_task_dependencies', task_id=task.task_id)
            
            return redirect('view_task', task_id=task.task_id)
    else:
        # Get employee id from query parameter if provided
        employee_id = request.GET.get('employee_id')
        initial_data = {
            'start_date': date.today(),
            'due_date': date.today() + timedelta(days=7)
        }
        
        if employee_id:
            try:
                employee = Employee.objects.get(pk=employee_id)
                initial_data['assignee'] = employee
            except Employee.DoesNotExist:
                pass
        
        form = TaskForm(initial=initial_data)
        
        # If current user is a manager, limit assignees to their department
        if request.user.role == 'Manager' and request.user.employee and request.user.employee.department:
            form.fields['assignee'].queryset = Employee.objects.filter(
                department=request.user.employee.department,
                status='Working'
            )
    
    return render(request, 'tasks/create_task.html', {'form': form})

@login_required
def view_task(request, task_id):
    """View task details"""
    task = get_object_or_404(Task, task_id=task_id)
    
    # Check if user has permission to view this task
    can_view = False
    
    if request.user.employee == task.assignee:  # Assignee
        can_view = True
    elif request.user == task.assigned_by:  # Creator
        can_view = True
    elif request.user.role in ['HR', 'Admin']:  # HR or Admin
        can_view = True
    elif request.user.role == 'Manager' and request.user.employee and task.department:
        # Manager in the same department
        if request.user.employee.department == task.department:
            can_view = True
    
    if not can_view:
        messages.error(request, "You don't have permission to view this task.")
        return redirect('dashboard')
    
    # Get comments
    comments = TaskComment.objects.filter(task=task).select_related('user')
    
    # Get dependencies
    dependencies = TaskDependency.objects.filter(task=task).select_related('dependent_on')
    dependent_tasks = TaskDependency.objects.filter(dependent_on=task).select_related('task')
    
    # Check if user can update task
    can_update = request.user.employee == task.assignee or request.user == task.assigned_by or request.user.role in ['HR', 'Admin']
    
    # Prepare comment form
    comment_form = TaskCommentForm()
    
    # Prepare status update form if user is assignee
    status_form = None
    if request.user.employee == task.assignee:
        status_form = TaskStatusUpdateForm(instance=task)
    
    return render(request, 'tasks/view_task.html', {
        'task': task,
        'comments': comments,
        'dependencies': dependencies,
        'dependent_tasks': dependent_tasks,
        'comment_form': comment_form,
        'status_form': status_form,
        'can_update': can_update
    })

@login_required
def update_task_status(request, task_id):
    """Update task status and progress"""
    task = get_object_or_404(Task, task_id=task_id)
    
    # Check if user is the assignee
    if request.user.employee != task.assignee:
        messages.error(request, "Only the assignee can update task status.")
        return redirect('view_task', task_id=task_id)
    
    if request.method == 'POST':
        form = TaskStatusUpdateForm(request.POST, instance=task)
        if form.is_valid():
            task_update = form.save(commit=False)
            
            # If marking as completed, set completion date
            if task_update.status == 'Completed' and not task_update.completion_date:
                task_update.completion_date = date.today()
                task_update.progress = 100
            
            task_update.save()
            
            # Add a comment about status change
            TaskComment.objects.create(
                task=task,
                user=request.user,
                comment=f"Status updated to {task_update.status} with {task_update.progress}% progress."
            )
            
            # Send notification to task creator
            create_notification(
                user=task.assigned_by,
                notification_type='Task',
                title='Task Status Updated',
                message=f'{request.user.employee.full_name} updated task "{task.title}" to {task_update.status}.',
                link=f'/tasks/view/{task_id}/'
            )
            
            messages.success(request, "Task status updated successfully.")
            return redirect('view_task', task_id=task_id)
    else:
        form = TaskStatusUpdateForm(instance=task)
    
    return render(request, 'tasks/update_task_status.html', {
        'form': form,
        'task': task
    })

@login_required
def add_task_comment(request, task_id):
    """Add a comment to a task"""
    task = get_object_or_404(Task, task_id=task_id)
    
    # Check if user can comment (same as view permission)
    can_comment = False
    
    if request.user.employee == task.assignee:  # Assignee
        can_comment = True
    elif request.user == task.assigned_by:  # Creator
        can_comment = True
    elif request.user.role in ['HR', 'Admin']:  # HR or Admin
        can_comment = True
    elif request.user.role == 'Manager' and request.user.employee and task.department:
        # Manager in the same department
        if request.user.employee.department == task.department:
            can_comment = True
    
    if not can_comment:
        messages.error(request, "You don't have permission to comment on this task.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = TaskCommentForm(request.POST, request.FILES)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task
            comment.user = request.user
            comment.save()
            
            # Send notification to task assignee (if not the commenter)
            if request.user.employee != task.assignee:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                assignee_user = User.objects.filter(employee=task.assignee).first()
                
                if assignee_user:
                    create_notification(
                        user=assignee_user,
                        notification_type='Task',
                        title='New Comment on Task',
                        message=f'{request.user.get_full_name()} commented on your task "{task.title}"',
                        link=f'/tasks/view/{task_id}/'
                    )
            
            # Also notify task creator if neither assignee nor commenter
            if request.user != task.assigned_by and request.user.employee != task.assignee:
                create_notification(
                    user=task.assigned_by,
                    notification_type='Task',
                    title='New Comment on Task',
                    message=f'{request.user.get_full_name()} commented on task "{task.title}"',
                    link=f'/tasks/view/{task_id}/'
                )
            
            messages.success(request, "Comment added successfully.")
            return redirect('view_task', task_id=task_id)
    else:
        form = TaskCommentForm()
    
    return render(request, 'tasks/add_comment.html', {
        'form': form,
        'task': task
    })

@login_required
@manager_required
def department_tasks(request):
    """View all tasks for the manager's department"""
    if not request.user.employee or not request.user.employee.department:
        messages.error(request, "You don't have a department assigned.")
        return redirect('dashboard')
    
    department = request.user.employee.department
    
    status_filter = request.GET.get('status', '')
    assignee_filter = request.GET.get('assignee', '')
    
    tasks = Task.objects.filter(department=department)
    
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    if assignee_filter:
        tasks = tasks.filter(assignee_id=assignee_filter)
    
    # Get all employees in the department for filter
    department_employees = Employee.objects.filter(department=department, status='Working')
    
    # Group tasks by status
    not_started = tasks.filter(status='Not Started').order_by('due_date')
    in_progress = tasks.filter(status='In Progress').order_by('due_date')
    on_hold = tasks.filter(status='On Hold').order_by('due_date')
    completed = tasks.filter(status='Completed').order_by('-completion_date')
    
    # Task statistics
    task_stats = {
        'total': tasks.count(),
        'not_started': not_started.count(),
        'in_progress': in_progress.count(),
        'on_hold': on_hold.count(),
        'completed': completed.count(),
        'overdue': tasks.filter(due_date__lt=date.today()).exclude(status__in=['Completed', 'Cancelled']).count()
    }
    
    return render(request, 'tasks/department_tasks.html', {
        'department': department,
        'not_started': not_started,
        'in_progress': in_progress,
        'on_hold': on_hold,
        'completed': completed,
        'department_employees': department_employees,
        'task_stats': task_stats,
        'status_filter': status_filter,
        'assignee_filter': assignee_filter
    })

@login_required
@manager_required
def add_task_dependencies(request, task_id):
    """Add dependencies to a task"""
    task = get_object_or_404(Task, task_id=task_id)
    
    # Check if user is the creator or has permission
    if request.user != task.assigned_by and request.user.role not in ['HR', 'Admin']:
        messages.error(request, "You don't have permission to add dependencies.")
        return redirect('view_task', task_id=task_id)
    
    # Get existing dependencies
    existing_dependencies = TaskDependency.objects.filter(task=task).values_list('dependent_on_id', flat=True)
    
    if request.method == 'POST':
        # Process the selected dependencies
        dependent_on_ids = request.POST.getlist('dependencies')
        
        # Remove unchecked dependencies
        TaskDependency.objects.filter(task=task).exclude(dependent_on_id__in=dependent_on_ids).delete()
        
        # Add new dependencies
        for dep_id in dependent_on_ids:
            if int(dep_id) != task.task_id:  # Prevent self-dependency
                TaskDependency.objects.get_or_create(
                    task=task,
                    dependent_on_id=dep_id
                )
        
        messages.success(request, "Task dependencies updated successfully.")
        return redirect('view_task', task_id=task_id)
    
    # Get potential dependency tasks (excluding the current task)
    # If manager, limit to department tasks
    if request.user.role == 'Manager' and request.user.employee and request.user.employee.department:
        potential_dependencies = Task.objects.filter(
            department=request.user.employee.department
        ).exclude(task_id=task_id)
    else:
        potential_dependencies = Task.objects.all().exclude(task_id=task_id)
    
    return render(request, 'tasks/add_dependencies.html', {
        'task': task,
        'potential_dependencies': potential_dependencies,
        'existing_dependencies': existing_dependencies
    })


@login_required
def my_tasks_calendar(request):
    """Calendar view of tasks for the current user"""
    if not request.user.employee:
        messages.error(request, "You don't have an employee profile.")
        return redirect('dashboard')
    
    # Get all tasks assigned to the user
    tasks = Task.objects.filter(assignee=request.user.employee)
    
    # Format for calendar
    calendar_events = []
    for task in tasks:
        # Determine color based on priority
        color = "#3498db"  # Default blue
        if task.priority == 'Low':
            color = "#2ecc71"  # Green
        elif task.priority == 'Medium':
            color = "#f39c12"  # Orange
        elif task.priority == 'High':
            color = "#e74c3c"  # Red
        elif task.priority == 'Urgent':
            color = "#9b59b6"  # Purple
        
        # Add completion status indicator
        title = f"{task.title}"
        if task.status == 'Completed':
            title = f"✅ {title}"
        elif task.is_overdue():
            title = f"⚠️ {title}"
        
        calendar_events.append({
            'id': task.task_id,
            'title': title,
            'start': task.start_date.isoformat(),
            'end': (task.due_date + timedelta(days=1)).isoformat(),  # Make end date inclusive
            'backgroundColor': color,
            'borderColor': color,
            'url': f'/tasks/view/{task.task_id}/',
            'extendedProps': {
                'status': task.status,
                'priority': task.priority,
                'progress': task.progress
            }
        })
    
    return render(request, 'tasks/my_tasks_calendar.html', {
        'calendar_events': calendar_events,
    })

@login_required
@check_module_permission('tasks', 'View')
def task_list(request):
    """View all tasks (admin/HR view)"""
    form = TaskFilterForm(request.GET)
    tasks = Task.objects.all().select_related('assignee', 'category', 'department')
    
    if form.is_valid():
        status = form.cleaned_data.get('status')
        priority = form.cleaned_data.get('priority')
        category = form.cleaned_data.get('category')
        assignee = form.cleaned_data.get('assignee')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        search = form.cleaned_data.get('search')
        
        if status:
            tasks = tasks.filter(status=status)
        
        if priority:
            tasks = tasks.filter(priority=priority)
        
        if category:
            tasks = tasks.filter(category=category)
        
        if assignee:
            tasks = tasks.filter(assignee=assignee)
        
        if start_date:
            tasks = tasks.filter(start_date__gte=start_date)
        
        if end_date:
            tasks = tasks.filter(due_date__lte=end_date)
        
        if search:
            tasks = tasks.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) |
                Q(assignee__full_name__icontains=search)
            )
    
    # Default ordering
    tasks = tasks.order_by('-created_date')
    
    # Task statistics
    task_stats = {
        'total': tasks.count(),
        'not_started': tasks.filter(status='Not Started').count(),
        'in_progress': tasks.filter(status='In Progress').count(),
        'on_hold': tasks.filter(status='On Hold').count(),
        'completed': tasks.filter(status='Completed').count(),
        'cancelled': tasks.filter(status='Cancelled').count(),
        'overdue': tasks.filter(due_date__lt=date.today(), status__in=['Not Started', 'In Progress', 'On Hold']).count()
    }
    
    return render(request, 'tasks/task_list.html', {
        'tasks': tasks,
        'form': form,
        'task_stats': task_stats
    })

@login_required
@check_module_permission('tasks', 'Edit')
def edit_task(request, task_id):
    """Edit an existing task"""
    task = get_object_or_404(Task, task_id=task_id)
    
    # Check if user has permission to edit
    if request.user != task.assigned_by and request.user.role not in ['HR', 'Admin']:
        messages.error(request, "You don't have permission to edit this task.")
        return redirect('view_task', task_id=task_id)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES, instance=task)
        if form.is_valid():
            task = form.save(commit=False)
            
            # Update department if assignee changed
            if task.assignee and task.assignee.department:
                task.department = task.assignee.department
            
            task.save()
            
            # Notify assignee if assignee has changed
            if 'assignee' in form.changed_data:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                assignee_user = User.objects.filter(employee=task.assignee).first()
                
                if assignee_user:
                    create_notification(
                        user=assignee_user,
                        notification_type='Task',
                        title='Task Assigned to You',
                        message=f'You have been assigned the task: {task.title}',
                        link=f'/tasks/view/{task.task_id}/'
                    )
            
            messages.success(request, "Task updated successfully.")
            return redirect('view_task', task_id=task_id)
    else:
        form = TaskForm(instance=task)
        
        # If current user is a manager, limit assignees to their department
        if request.user.role == 'Manager' and request.user.employee and request.user.employee.department:
            form.fields['assignee'].queryset = Employee.objects.filter(
                department=request.user.employee.department,
                status='Working'
            )
    
    return render(request, 'tasks/edit_task.html', {
        'form': form,
        'task': task
    })

@login_required
@check_module_permission('tasks', 'Delete')
def delete_task(request, task_id):
    """Delete a task"""
    task = get_object_or_404(Task, task_id=task_id)
    
    # Check if user has permission to delete
    if request.user != task.assigned_by and request.user.role not in ['HR', 'Admin']:
        messages.error(request, "You don't have permission to delete this task.")
        return redirect('view_task', task_id=task_id)
    
    if request.method == 'POST':
        # Check if the task has dependents
        if TaskDependency.objects.filter(dependent_on=task).exists():
            messages.error(request, "This task cannot be deleted because other tasks depend on it. Remove the dependencies first.")
            return redirect('view_task', task_id=task_id)
        
        # Delete the task
        task.delete()
        messages.success(request, "Task deleted successfully.")
        
        # Redirect to appropriate page
        if request.user.role in ['HR', 'Admin']:
            return redirect('task_list')
        elif request.user.role == 'Manager':
            return redirect('department_tasks')
        else:
            return redirect('my_tasks')
    
    return render(request, 'tasks/delete_task.html', {'task': task})

@login_required
def delete_task_comment(request, comment_id):
    """Delete a task comment"""
    comment = get_object_or_404(TaskComment, comment_id=comment_id)
    task_id = comment.task.task_id
    
    # Check if user has permission to delete this comment
    if comment.user != request.user and request.user.role not in ['HR', 'Admin']:
        messages.error(request, "You don't have permission to delete this comment.")
        return redirect('view_task', task_id=task_id)
    
    if request.method == 'POST':
        comment.delete()
        messages.success(request, "Comment deleted successfully.")
    
    return redirect('view_task', task_id=task_id)

@login_required
def team_tasks(request):
    """View tasks for team members (for managers)"""
    if not request.user.employee or not request.user.employee.department:
        messages.error(request, "You don't have a department assigned.")
        return redirect('dashboard')
    
    # This is similar to department_tasks but with a different layout
    department = request.user.employee.department
    
    # Get all employees in the department for filter
    department_employees = Employee.objects.filter(department=department, status='Working')
    
    # Handle form filtering
    form = TaskFilterForm(request.GET)
    form.fields['assignee'].queryset = department_employees
    
    tasks = Task.objects.filter(department=department)
    
    if form.is_valid():
        status = form.cleaned_data.get('status')
        priority = form.cleaned_data.get('priority')
        category = form.cleaned_data.get('category')
        assignee = form.cleaned_data.get('assignee')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        search = form.cleaned_data.get('search')
        
        if status:
            tasks = tasks.filter(status=status)
        
        if priority:
            tasks = tasks.filter(priority=priority)
        
        if category:
            tasks = tasks.filter(category=category)
        
        if assignee:
            tasks = tasks.filter(assignee=assignee)
        
        if start_date:
            tasks = tasks.filter(start_date__gte=start_date)
        
        if end_date:
            tasks = tasks.filter(due_date__lte=end_date)
        
        if search:
            tasks = tasks.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search)
            )
    
    # Group tasks by employee
    employee_tasks = {}
    for employee in department_employees:
        employee_tasks[employee] = {
            'active': tasks.filter(assignee=employee).exclude(status__in=['Completed', 'Cancelled']),
            'completed': tasks.filter(assignee=employee, status='Completed'),
            'overdue': tasks.filter(assignee=employee, due_date__lt=date.today()).exclude(status__in=['Completed', 'Cancelled'])
        }
    
    return render(request, 'tasks/team_tasks.html', {
        'department': department,
        'employee_tasks': employee_tasks,
        'form': form
    })

@login_required
@check_module_permission('tasks', 'View')
def task_category_list(request):
    """List task categories"""
    categories = TaskCategory.objects.all().order_by('-is_active', 'name')
    
    # Count tasks in each category
    for category in categories:
        category.task_count = Task.objects.filter(category=category).count()
    
    return render(request, 'tasks/category_list.html', {'categories': categories})

@login_required
@check_module_permission('tasks', 'Edit')
def task_category_create(request):
    """Create a new task category"""
    if request.method == 'POST':
        form = TaskCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Task category created successfully.")
            return redirect('task_category_list')
    else:
        form = TaskCategoryForm()
    
    return render(request, 'tasks/category_form.html', {'form': form, 'is_new': True})

@login_required
@check_module_permission('tasks', 'Edit')
def task_category_edit(request, category_id):
    """Edit a task category"""
    category = get_object_or_404(TaskCategory, category_id=category_id)
    
    if request.method == 'POST':
        form = TaskCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Task category updated successfully.")
            return redirect('task_category_list')
    else:
        form = TaskCategoryForm(instance=category)
    
    return render(request, 'tasks/category_form.html', {'form': form, 'category': category, 'is_new': False})

@login_required
@check_module_permission('tasks', 'Delete')
def task_category_delete(request, category_id):
    """Delete a task category"""
    category = get_object_or_404(TaskCategory, category_id=category_id)
    
    # Check if there are tasks using this category
    task_count = Task.objects.filter(category=category).count()
    
    if request.method == 'POST':
        if task_count > 0 and not request.POST.get('confirm_delete'):
            messages.error(request, f"This category is used by {task_count} tasks. Please confirm deletion.")
            return render(request, 'tasks/category_delete.html', {'category': category, 'task_count': task_count, 'show_confirm': True})
        
        # If there are tasks, set their category to null
        Task.objects.filter(category=category).update(category=None)
        
        category.delete()
        messages.success(request, "Task category deleted successfully.")
        return redirect('task_category_list')
    
    return render(request, 'tasks/category_delete.html', {'category': category, 'task_count': task_count})

@login_required
@check_module_permission('tasks', 'View')
def task_report(request):
    """Generate task reports and statistics"""
    # Date range for the report
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        # Default to last 30 days
        start_date = date.today() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = date.today()
    
    # Filter tasks by date range
    tasks = Task.objects.filter(
        Q(created_date__date__gte=start_date) & 
        Q(created_date__date__lte=end_date)
    )
    
    # Overall statistics
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status='Completed').count()
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    avg_completion_time = 0
    completed_with_dates = tasks.filter(
        status='Completed', 
        completion_date__isnull=False
    )
    
    if completed_with_dates.exists():
        total_days = sum([(task.completion_date - task.start_date).days for task in completed_with_dates])
        avg_completion_time = total_days / completed_with_dates.count()
    
    # Tasks by status
    status_counts = tasks.values('status').annotate(count=Count('status')).order_by('status')
    
    # Tasks by priority
    priority_counts = tasks.values('priority').annotate(count=Count('priority')).order_by('priority')
    
    # Tasks by department
    dept_counts = tasks.values('department__department_name').annotate(count=Count('department')).order_by('department__department_name')
    
    # Tasks by category
    category_counts = tasks.values('category__name').annotate(count=Count('category')).order_by('category__name')
    
    # Overdue tasks
    overdue_tasks = tasks.filter(due_date__lt=date.today()).exclude(status__in=['Completed', 'Cancelled'])
    overdue_count = overdue_tasks.count()
    overdue_rate = (overdue_count / total_tasks * 100) if total_tasks > 0 else 0
    
    # Tasks by assignee (top 10)
    assignee_counts = tasks.values('assignee__full_name').annotate(count=Count('assignee')).order_by('-count')[:10]
    
    # Tasks created over time
    tasks_by_date = tasks.extra({
        'created_date_day': "DATE(created_date)"
    }).values('created_date_day').annotate(count=Count('task_id')).order_by('created_date_day')
    
    # Prepare chart data
    date_labels = [entry['created_date_day'] for entry in tasks_by_date]
    date_counts = [entry['count'] for entry in tasks_by_date]
    
    # Status labels and data for chart
    status_labels = [entry['status'] for entry in status_counts]
    status_data = [entry['count'] for entry in status_counts]
    
    # Priority labels and data for chart
    priority_labels = [entry['priority'] for entry in priority_counts]
    priority_data = [entry['count'] for entry in priority_counts]
    
    return render(request, 'tasks/task_report.html', {
        'start_date': start_date,
        'end_date': end_date,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'completion_rate': round(completion_rate, 2),
        'avg_completion_time': round(avg_completion_time, 2),
        'status_counts': status_counts,
        'priority_counts': priority_counts,
        'dept_counts': dept_counts,
        'category_counts': category_counts,
        'overdue_count': overdue_count,
        'overdue_rate': round(overdue_rate, 2),
        'assignee_counts': assignee_counts,
        
        # Chart data
        'date_labels': date_labels,
        'date_counts': date_counts,
        'status_labels': status_labels,
        'status_data': status_data,
        'priority_labels': priority_labels,
        'priority_data': priority_data
    })

@login_required
@check_module_permission('tasks', 'View')
def export_tasks(request):
    """Export tasks to CSV"""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tasks_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Title', 'Description', 'Category', 'Assignee', 'Department',
        'Priority', 'Status', 'Start Date', 'Due Date', 'Completion Date',
        'Progress', 'Is Recurring', 'Recurrence Pattern', 'Created By', 'Created Date'
    ])
    
    tasks = Task.objects.all().select_related(
        'category', 'assignee', 'department', 'assigned_by'
    )
    
    # Apply filters if provided
    status = request.GET.get('status')
    if status:
        tasks = tasks.filter(status=status)
    
    for task in tasks:
        writer.writerow([
            task.task_id,
            task.title,
            task.description,
            task.category.name if task.category else '',
            task.assignee.full_name if task.assignee else '',
            task.department.department_name if task.department else '',
            task.priority,
            task.status,
            task.start_date,
            task.due_date,
            task.completion_date or '',
            task.progress,
            'Yes' if task.is_recurring else 'No',
            task.recurrence_pattern or '',
            task.assigned_by.get_full_name() if task.assigned_by else '',
            task.created_date.strftime('%Y-%m-%d %H:%M')
        ])
    
    return response