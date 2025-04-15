from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Avg, Q, F, Case, When, Value, IntegerField, DateTimeField,  DecimalField
from django.db.models.functions import TruncMonth, TruncDay, Coalesce
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateformat import format
from django.utils.translation import gettext as _

from datetime import date, datetime, timedelta
import calendar
import json
import random

# Model imports
from employee.models import Employee, Department, Position, EmployeeCertificate
from attendance.models import Attendance, WorkShift, ShiftAssignment
from leave.models import LeaveRequest, LeaveBalance
from salary.models import Salary, SalaryAdvance, SalaryGrade, EmployeeSalaryGrade
from performance.models import EmployeeEvaluation, RewardsAndDisciplinary, KPI
from training.models import TrainingCourse, TrainingParticipation
from contract.models import EmploymentContract
from accounts.models import User, Permission, SystemLog
from expenses.models import ExpenseClaim, ExpenseItem
from assets.models import Asset, AssetAssignment
from tasks.models import Task, TaskComment
from employee.forms import EmployeeBasicInfoForm, EmployeeProfileForm, EmployeeLocationForm


@login_required
def dashboard(request):
    """
    Main dashboard router that redirects to the appropriate role-based dashboard.
    Checks the user's role and redirects accordingly.
    """
    if not request.user.is_active:
        messages.error(request, _('Tài khoản của bạn không hoạt động'))
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
    """
    Dashboard for regular employees showing personal information and statistics.
    Displays:
    - Attendance status
    - Leave requests and balances
    - Upcoming training
    - Expiring certificates
    - Performance evaluations
    - Salary information
    - Recent tasks
    """
    if not request.user.employee:
        messages.info(request, _('Vui lòng hoàn thành hồ sơ nhân viên của bạn'))
        return redirect('employee_edit_profile')
    
    employee = request.user.employee
    today = date.today()
    current_month = today.replace(day=1)
    current_year = today.year
    
    # Get important dates for queries
    month_start = date(today.year, today.month, 1)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    year_start = date(today.year, 1, 1)
    
    # Attendance summary
    today_attendance = Attendance.objects.filter(
        employee=employee,
        work_date=today
    ).first()
    
    # Monthly attendance statistics
    attendance_stats = Attendance.objects.filter(
        employee=employee,
        work_date__gte=month_start,
        work_date__lte=today
    ).aggregate(
        total=Count('attendance_id'),
        present=Count('attendance_id', filter=Q(status='Present')),
        absent=Count('attendance_id', filter=Q(status='Absent')),
        on_leave=Count('attendance_id', filter=Q(status='On Leave')),
        late_count=Count('attendance_id', filter=Q(time_in__isnull=False) & 
                        Q(shift__isnull=False) & 
                        Q(time_in__gt=F('shift__start_time')))
    )
    
    # Current week attendance data for mini-graph
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    daily_hours = []
    for day_offset in range(7):
        current_day = week_start + timedelta(days=day_offset)
        if current_day <= today:
            day_record = Attendance.objects.filter(
                employee=employee,
                work_date=current_day
            ).first()
            
            if day_record and day_record.actual_work_hours:
                daily_hours.append(float(day_record.actual_work_hours))
            else:
                daily_hours.append(0)
        else:
            daily_hours.append(None)  # Future dates
    
    # Leave information
    pending_leaves = LeaveRequest.objects.filter(
        employee=employee,
        status='Pending'
    ).order_by('-start_date')[:3]
    
    recent_leaves = LeaveRequest.objects.filter(
        employee=employee
    ).exclude(status='Pending').order_by('-updated_date')[:3]
    
    # Calculate leave balances
    leave_balances = LeaveBalance.objects.filter(
        employee=employee,
        year=current_year
    )
    
    if not leave_balances.exists():
        # If no leave balances exist, use standard values
        annual_balance = 12  # Example: 12 days of annual leave per year
        sick_balance = 15    # Example: 15 days of sick leave per year
    else:
        # Sum up the remaining days by leave type
        annual_balance = sum(balance.remaining_days for balance in leave_balances if balance.leave_type == 'Annual Leave')
        sick_balance = sum(balance.remaining_days for balance in leave_balances if balance.leave_type == 'Sick Leave')
    
    leave_days_used = LeaveRequest.objects.filter(
        employee=employee,
        status='Approved',
        start_date__year=today.year
    ).aggregate(total=Coalesce(Sum('leave_days'), 0, output_field=DecimalField()))['total']

    
    # Upcoming training
    upcoming_training = TrainingParticipation.objects.filter(
        employee=employee,
        status__in=['Registered', 'Participating'],
        course__start_date__gte=today
    ).select_related('course').order_by('course__start_date')[:3]
    
    # Recent completed training
    completed_training = TrainingParticipation.objects.filter(
        employee=employee,
        status='Completed'
    ).select_related('course').order_by('-actual_completion_date')[:3]
    
    # Expiring certificates
    expiring_certificates = EmployeeCertificate.objects.filter(
        employee=employee,
        status='Valid',
        expiry_date__lte=today + timedelta(days=90)
    ).order_by('expiry_date')[:3]
    
    # Recent evaluations
    recent_evaluations = EmployeeEvaluation.objects.filter(
        employee=employee
    ).order_by('-year', '-month')[:5]
    
    # Calculate average achievement rate for current year
    performance_stats = EmployeeEvaluation.objects.filter(
    employee=employee,
    year=current_year
    ).aggregate(
        avg_rate=Coalesce(Avg('achievement_rate'), 0, output_field=DecimalField()),
        count=Count('evaluation_id')
    )
    
    # Latest salary
    latest_salary = Salary.objects.filter(
        employee=employee
    ).order_by('-year', '-month').first()
    
    # Salary trend (last 6 months)
    salary_trend = []
    salary_months = []
    for i in range(5, -1, -1):
        trend_date = (today.replace(day=1) - timedelta(days=1*i*30))
        month_name = trend_date.strftime('%b')
        salary_months.append(month_name)
        
        month_salary = Salary.objects.filter(
            employee=employee,
            month=trend_date.month,
            year=trend_date.year
        ).first()
        
        if month_salary:
            salary_trend.append(float(month_salary.net_salary))
        else:
            salary_trend.append(None)
    
    # Tasks assigned to employee
    active_tasks = Task.objects.filter(
        assignee=employee,
        status__in=['Not Started', 'In Progress']
    ).order_by('due_date')[:5]
    
    overdue_tasks = [task for task in active_tasks if task.is_overdue()]
    
    # Contract information
    current_contract = EmploymentContract.objects.filter(
        employee=employee,
        status='Active'
    ).order_by('-start_date').first()
    
    # Announcements (example - in a real system, you'd have an Announcement model)
    announcements = [
        {'title': 'Company Picnic', 'date': today + timedelta(days=15)},
        {'title': 'New Benefits Package', 'date': today - timedelta(days=2)},
    ]
    
    # Assets assigned to employee
    assigned_assets = AssetAssignment.objects.filter(
        employee=employee,
        status='Assigned'
    ).select_related('asset')[:5]
    
    context = {
        'employee': employee,
        'today': today,
        
        # Attendance data
        'today_attendance': today_attendance,
        'attendance_stats': attendance_stats,
        'daily_hours': daily_hours,
        'weekdays': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        
        # Leave data
        'pending_leaves': pending_leaves,
        'recent_leaves': recent_leaves,
        'annual_balance': annual_balance,
        'sick_balance': sick_balance,
        'leave_days_used': leave_days_used,
        
        # Training data
        'upcoming_training': upcoming_training,
        'completed_training': completed_training,
        
        # Certificate data
        'expiring_certificates': expiring_certificates,
        
        # Performance data
        'recent_evaluations': recent_evaluations,
        'performance_stats': performance_stats,
        
        # Salary data
        'latest_salary': latest_salary,
        'salary_trend': salary_trend,
        'salary_months': salary_months,
        
        # Task data
        'active_tasks': active_tasks,
        'overdue_tasks': overdue_tasks,
        
        # Contract data
        'current_contract': current_contract,
        
        # Extra data
        'announcements': announcements,
        'assigned_assets': assigned_assets,
    }
    
    return render(request, 'dashboard/employee_dashboard.html', context)


@login_required
def manager_dashboard(request):
    """
    Dashboard for managers showing team statistics and department performance.
    Displays:
    - Team member list and status
    - Department attendance summary
    - Pending leave requests
    - Performance metrics by team member
    - Training completion rates
    - Department expense overview
    - Task status by team member
    """
    if not request.user.employee or request.user.role != 'Manager':
        messages.error(request, _('Bạn không có quyền truy cập của quản lý'))
        return redirect('dashboard')
    
    manager = request.user.employee
    department = manager.department
    today = date.today()
    current_month = today.replace(day=1)
    
    if not department:
        messages.warning(request, _('Bạn chưa được phân vào phòng ban nào'))
        return redirect('employee_dashboard')
    
    # Team members (excluding the manager)
    team_members = Employee.objects.filter(
        department=department,
        status='Working'
    ).exclude(pk=manager.pk)
    
    # Calculate team statistics
    team_stats = {
        'total': team_members.count(),
        'male': team_members.filter(gender='Male').count(),
        'female': team_members.filter(gender='Female').count(),
        'other': team_members.filter(gender='Other').count(),
    }
    
    # Pending leave requests for approval
    pending_leaves = LeaveRequest.objects.filter(
        employee__department=department,
        status='Pending'
    ).select_related('employee').order_by('start_date')[:5]
    
    # Today's attendance for the department
    today_attendance = Attendance.objects.filter(
        employee__department=department,
        work_date=today
    ).select_related('employee')
    
    attendance_summary = {
        'present': today_attendance.filter(status='Present').count(),
        'absent': today_attendance.filter(status='Absent').count(),
        'on_leave': today_attendance.filter(status='On Leave').count(),
        'total': team_members.count(),
        'percentage': round((today_attendance.filter(status='Present').count() / team_members.count() * 100) 
                           if team_members.count() > 0 else 0)
    }
    
    # Attendance trend for the month (department)
    attendance_trend = []
    trend_dates = []
    
    # Get the first day of month to current day
    start_of_month = date(today.year, today.month, 1)
    days_in_current_month = (today - start_of_month).days + 1
    
    for day in range(days_in_current_month):
        current_date = start_of_month + timedelta(days=day)
        if current_date.weekday() < 5:  # Only weekdays (Monday to Friday)
            trend_dates.append(current_date.strftime('%d'))
            
            daily_attendance = Attendance.objects.filter(
                employee__department=department,
                work_date=current_date,
                status='Present'
            ).count()
            
            attendance_trend.append(daily_attendance)
    
    # Performance metrics
    # Get last completed month and year
    if today.month == 1:
        last_month = 12
        last_year = today.year - 1
    else:
        last_month = today.month - 1
        last_year = today.year
    
    performance_data = EmployeeEvaluation.objects.filter(
        employee__department=department,
        month=last_month,
        year=last_year
    ).select_related('employee', 'kpi')
    
    # Calculate average performance by employee
    employee_performance = {}
    for evaluation in performance_data:
        employee_id = evaluation.employee.pk
        if employee_id not in employee_performance:
            employee_performance[employee_id] = {
                'employee': evaluation.employee,
                'total_rate': 0,
                'count': 0,
                'average': 0
            }
        
        employee_performance[employee_id]['total_rate'] += evaluation.achievement_rate or 0
        employee_performance[employee_id]['count'] += 1
    
    # Calculate averages
    for emp_id in employee_performance:
        if employee_performance[emp_id]['count'] > 0:
            employee_performance[emp_id]['average'] = round(
                employee_performance[emp_id]['total_rate'] / 
                employee_performance[emp_id]['count'], 2
            )
    
    # Sort by average performance
    top_performers = sorted(
        employee_performance.values(), 
        key=lambda x: x['average'], 
        reverse=True
    )[:5]
    
    # Department training stats
    training_stats = TrainingParticipation.objects.filter(
        employee__department=department
    ).aggregate(
        total=Count('participation_id'),
        completed=Count('participation_id', filter=Q(status='Completed')),
        registered=Count('participation_id', filter=Q(status='Registered')),
        participating=Count('participation_id', filter=Q(status='Participating')),
        cancelled=Count('participation_id', filter=Q(status='Cancelled'))
    )
    
    if training_stats['total'] > 0:
        training_stats['completion_rate'] = round(training_stats['completed'] / training_stats['total'] * 100, 1)
    else:
        training_stats['completion_rate'] = 0
    
    # Department expense summary (current year)
    expense_data = ExpenseClaim.objects.filter(
        employee__department=department,
        status__in=['Approved', 'Paid'],
        submission_date__year=today.year
    )
    
    expense_summary = expense_data.aggregate(
        total_amount=Coalesce(Sum('total_amount'), 0),
        count=Count('claim_id')
    )
    
    # Expense trend by month
    expense_trend = []
    expense_months = []
    
    for month in range(1, 13):
        if date(today.year, month, 1) <= today:
            month_name = date(today.year, month, 1).strftime('%b')
            expense_months.append(month_name)
            
            month_expenses = ExpenseClaim.objects.filter(
                employee__department=department,
                status__in=['Approved', 'Paid'],
                submission_date__year=today.year,
                submission_date__month=month
            ).aggregate(total=Coalesce(Sum('total_amount'), 0))
            
            expense_trend.append(float(month_expenses['total']))
    
    # Team tasks overview
    task_summary = Task.objects.filter(
        assignee__department=department
    ).aggregate(
        total=Count('task_id'),
        not_started=Count('task_id', filter=Q(status='Not Started')),
        in_progress=Count('task_id', filter=Q(status='In Progress')),
        completed=Count('task_id', filter=Q(status='Completed')),
        overdue=Count('task_id', filter=Q(status__in=['Not Started', 'In Progress']) & Q(due_date__lt=today))
    )
    
    if task_summary['total'] > 0:
        task_summary['completion_rate'] = round(task_summary['completed'] / task_summary['total'] * 100, 1)
    else:
        task_summary['completion_rate'] = 0
    
    # Recent task activity
    recent_tasks = Task.objects.filter(
        assignee__department=department
    ).order_by('-updated_date')[:5]
    
    # Team position distribution
    position_distribution = Employee.objects.filter(
        department=department,
        status='Working'
    ).values('position__position_name').annotate(
        count=Count('employee_id')
    ).order_by('-count')
    
    context = {
        'manager': manager,
        'department': department,
        'today': today,
        
        # Team data
        'team_members': team_members,
        'team_stats': team_stats,
        'position_distribution': position_distribution,
        
        # Attendance data
        'attendance_summary': attendance_summary,
        'trend_dates': trend_dates,
        'attendance_trend': attendance_trend,
        
        # Leave data
        'pending_leaves': pending_leaves,
        
        # Performance data
        'top_performers': top_performers,
        
        # Training data
        'training_stats': training_stats,
        
        # Expense data
        'expense_summary': expense_summary,
        'expense_months': expense_months,
        'expense_trend': expense_trend,
        
        # Task data
        'task_summary': task_summary,
        'recent_tasks': recent_tasks,
    }
    
    return render(request, 'dashboard/manager_dashboard.html', context)


@login_required
def hr_dashboard(request):
    """
    Enhanced HR dashboard with advanced data visualization.
    Displays:
    - Company-wide employee metrics
    - Department statistics
    - Gender distribution
    - Attendance patterns
    - Leave statistics
    - Monthly employee changes (hires vs separations)
    - Contract expirations
    - Performance evaluations
    - Salary distributions
    - Expense trends
    - Asset allocations
    - Task completion rates
    """
    if request.user.role not in ['HR', 'Admin']:
        messages.error(request, _('Bạn không có quyền truy cập của HR'))
        return redirect('dashboard')
    
    today = date.today()
    year = today.year
    month = today.month
    
    # Get start and end of current month
    current_month_start = date(year, month, 1)
    next_month = month + 1 if month < 12 else 1
    next_month_year = year if month < 12 else year + 1
    current_month_end = date(next_month_year, next_month, 1) - timedelta(days=1)
    
    # Employee statistics
    total_employees = Employee.objects.filter(status='Working').count()
    new_employees_this_month = Employee.objects.filter(
        hire_date__gte=current_month_start,
        hire_date__lte=current_month_end
    ).count()
    
    # Overall employee statistics
    employee_stats = {
        'total': total_employees,
        'new_this_month': new_employees_this_month,
        'resigned_this_month': Employee.objects.filter(
            status='Resigned',
            updated_date__gte=current_month_start,
            updated_date__lte=current_month_end
        ).count(),
        'on_leave': Employee.objects.filter(status='On Leave').count(),
        'total_male': Employee.objects.filter(status='Working', gender='Male').count(),
        'total_female': Employee.objects.filter(status='Working', gender='Female').count(),
        'total_other': Employee.objects.filter(status='Working', gender='Other').count(),
    }
    
    # Calculate employee statistics by department
    departments = Department.objects.filter(status=1)
    dept_employee_counts = []
    dept_names = []
    dept_counts = []
    
    for dept in departments:
        count = Employee.objects.filter(department=dept, status='Working').count()
        dept_employee_counts.append({
            'name': dept.department_name,
            'count': count
        })
        dept_names.append(dept.department_name)
        dept_counts.append(count)
    
    # Gender distribution
    gender_counts = list(Employee.objects.filter(status='Working')
                         .values('gender')
                         .annotate(count=Count('employee_id'))
                         .order_by('gender'))
    
    # Add missing gender values with count 0
    gender_values = ['Male', 'Female', 'Other']
    existing_genders = [g['gender'] for g in gender_counts if g['gender'] is not None]
    for gender in gender_values:
        if gender not in existing_genders:
            gender_counts.append({'gender': gender, 'count': 0})
    
    gender_labels = [g['gender'] if g['gender'] is not None else 'Unknown' for g in gender_counts]
    gender_data = [g['count'] for g in gender_counts]
    
    # Attendance overview for current month
    attendance_by_date = (Attendance.objects
                         .filter(work_date__gte=current_month_start, work_date__lte=current_month_end)
                         .values('work_date', 'status')
                         .annotate(count=Count('attendance_id'))
                         .order_by('work_date'))
    
    attendance_dates = []
    present_counts = []
    absent_counts = []
    leave_counts = []
    
    # Initialize counts for each day in the month
    date_dict = {}
    current_date = current_month_start
    while current_date <= current_month_end:
        if current_date.weekday() < 5:  # Only include weekdays (Monday=0, Sunday=6)
            date_dict[current_date] = {'Present': 0, 'Absent': 0, 'On Leave': 0}
        current_date += timedelta(days=1)
    
    # Fill in actual counts
    for item in attendance_by_date:
        work_date = item['work_date']
        if work_date in date_dict:
            date_dict[work_date][item['status']] = item['count']
    
    # Convert to lists for chart
    for date_val, counts in sorted(date_dict.items()):
        attendance_dates.append(format(date_val, 'd'))  # Day of month as number
        present_counts.append(counts['Present'])
        absent_counts.append(counts['Absent'])
        leave_counts.append(counts['On Leave'])
    
    # Leave statistics
    leave_by_type = (LeaveRequest.objects
                    .filter(status='Approved', start_date__year=year)
                    .values('leave_type')
                    .annotate(count=Count('request_id'), days=Sum('leave_days'))
                    .order_by('leave_type'))
    
    leave_types = [l['leave_type'] for l in leave_by_type]
    leave_counts_by_type = [l['count'] for l in leave_by_type]
    leave_days_by_type = [float(l['days']) for l in leave_by_type]
    
    # Pending leave requests
    pending_leave_count = LeaveRequest.objects.filter(status='Pending').count()
    
    # Monthly employee changes (hires vs separations)
    employee_changes = []
    labels = []
    hires = []
    separations = []
    
    # Get data for the last 12 months
    for i in range(11, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=i * 30)
        month_start = date(month_date.year, month_date.month, 1)
        
        # Get last day of month
        if month_date.month == 12:
            month_end = date(month_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(month_date.year, month_date.month + 1, 1) - timedelta(days=1)
        
        # Count hires and separations
        month_hires = Employee.objects.filter(
            hire_date__gte=month_start,
            hire_date__lte=month_end
        ).count()
        
        month_separations = Employee.objects.filter(
            status='Resigned',
            updated_date__gte=month_start,
            updated_date__lte=month_end
        ).count()
        
        labels.append(month_date.strftime('%b %Y'))
        hires.append(month_hires)
        separations.append(month_separations)
    
    # Upcoming contract expirations
    thirty_days_later = today + timedelta(days=30)
    expiring_contracts = EmploymentContract.objects.filter(
        end_date__isnull=False,
        end_date__gte=today,
        end_date__lte=thirty_days_later,
        status='Active'
    ).select_related('employee').order_by('end_date')
    
    # Performance overview
    avg_performance_by_dept = (EmployeeEvaluation.objects
                              .filter(year=year)
                              .values('employee__department__department_name')
                              .annotate(avg_score=Avg('achievement_rate'))
                              .order_by('employee__department__department_name'))
    
    perf_dept_names = [p['employee__department__department_name'] or 'No Department' for p in avg_performance_by_dept]
    perf_dept_scores = [float(p['avg_score']) for p in avg_performance_by_dept]
    
    # Salary distribution
    salary_distribution = (Salary.objects
                          .filter(month=month, year=year)
                          .values('employee__department__department_name')
                          .annotate(total_salary=Sum('net_salary'), avg_salary=Avg('net_salary'))
                          .order_by('employee__department__department_name'))
    
    # If no salary data for current month, use previous month
    if not salary_distribution:
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        salary_distribution = (Salary.objects
                              .filter(month=prev_month, year=prev_year)
                              .values('employee__department__department_name')
                              .annotate(total_salary=Sum('net_salary'), avg_salary=Avg('net_salary'))
                              .order_by('employee__department__department_name'))
    
    salary_dept_names = [s['employee__department__department_name'] or 'No Department' for s in salary_distribution]
    salary_dept_totals = [float(s['total_salary']) for s in salary_distribution]
    salary_dept_avgs = [float(s['avg_salary']) for s in salary_distribution]
    
    # Expense trends
    expense_by_month = []
    expense_labels = []
    expense_amounts = []
    
    # Get data for the last 6 months
    for i in range(5, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=i * 30)
        month_start = date(month_date.year, month_date.month, 1)
        
        # Get last day of month
        if month_date.month == 12:
            month_end = date(month_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(month_date.year, month_date.month + 1, 1) - timedelta(days=1)
        
        # Sum expenses
        month_expenses = ExpenseClaim.objects.filter(
            status='Paid',
            payment_date__gte=month_start,
            payment_date__lte=month_end
        ).aggregate(total=Sum('total_amount'))
        
        expense_labels.append(month_date.strftime('%b %Y'))
        expense_amounts.append(float(month_expenses['total'] or 0))
    
    # Asset allocation
    asset_allocation = (Asset.objects
                       .filter(status='Assigned')
                       .values('category__name')
                       .annotate(count=Count('asset_id'))
                       .order_by('category__name'))
    
    asset_categories = [a['category__name'] or 'Uncategorized' for a in asset_allocation]
    asset_counts = [a['count'] for a in asset_allocation]
    
    # Task completion rates
    task_completion = (Task.objects
                      .filter(due_date__year=year)
                      .values('status')
                      .annotate(count=Count('task_id'))
                      .order_by('status'))
    
    task_statuses = [t['status'] for t in task_completion]
    task_counts = [t['count'] for t in task_completion]
    
    # Upcoming birthdays in the next 30 days
    thirty_days_from_now = today + timedelta(days=30)
    upcoming_birthdays = []
    
    employees_with_birth_dates = Employee.objects.filter(
        status='Working',
        date_of_birth__isnull=False
    )
    
    for employee in employees_with_birth_dates:
        # Calculate next birthday
        birth_date = employee.date_of_birth
        next_birthday = date(today.year, birth_date.month, birth_date.day)
        
        # If birthday has already passed this year, use next year's date
        if next_birthday < today:
            next_birthday = date(today.year + 1, birth_date.month, birth_date.day)
        
        # Check if birthday is within the next 30 days
        if next_birthday <= thirty_days_from_now:
            days_until = (next_birthday - today).days
            upcoming_birthdays.append({
                'id': employee.employee_id,
                'name': employee.full_name,
                'date': birth_date,
                'next_birthday': next_birthday,
                'days_until': days_until
            })
    
    # Sort by days until birthday
    upcoming_birthdays = sorted(upcoming_birthdays, key=lambda x: x['days_until'])[:5]
    
    # Pending onboarding (just a sample, you would implement this if you have an onboarding model)
    pending_onboarding = []
    
    # Combine all data for the dashboard
    context = {
        'today': today,
        'employee_stats': employee_stats,
        'total_employees': total_employees,
        'new_employees_this_month': new_employees_this_month,
        'dept_employee_counts': dept_employee_counts,
        'expiring_contracts': expiring_contracts,
        'upcoming_birthdays': upcoming_birthdays,
        'pending_onboarding': pending_onboarding,
        'pending_leaves': pending_leave_count,
        
        # Chart data
        'dept_names_json': json.dumps(dept_names),
        'dept_counts_json': json.dumps(dept_counts),
        
        'gender_labels_json': json.dumps(gender_labels),
        'gender_data_json': json.dumps(gender_data),
        
        'attendance_dates_json': json.dumps(attendance_dates),
        'present_counts_json': json.dumps(present_counts),
        'absent_counts_json': json.dumps(absent_counts),
        'leave_counts_json': json.dumps(leave_counts),
        
        'leave_types_json': json.dumps(leave_types),
        'leave_counts_by_type_json': json.dumps(leave_counts_by_type),
        'leave_days_by_type_json': json.dumps(leave_days_by_type),
        
        'employee_change_labels_json': json.dumps(labels),
        'hires_json': json.dumps(hires),
        'separations_json': json.dumps(separations),
        
        'perf_dept_names_json': json.dumps(perf_dept_names),
        'perf_dept_scores_json': json.dumps(perf_dept_scores),
        
        'salary_dept_names_json': json.dumps(salary_dept_names),
        'salary_dept_totals_json': json.dumps(salary_dept_totals),
        'salary_dept_avgs_json': json.dumps(salary_dept_avgs),
        
        'expense_labels_json': json.dumps(expense_labels),
        'expense_amounts_json': json.dumps(expense_amounts),
        
        'asset_categories_json': json.dumps(asset_categories),
        'asset_counts_json': json.dumps(asset_counts),
        
        'task_statuses_json': json.dumps(task_statuses),
        'task_counts_json': json.dumps(task_counts),
    }
    
    return render(request, 'dashboard/hr_dashboard.html', context)


@login_required
def admin_dashboard(request):
    """
    Dashboard for admin users with system metrics and management features.
    Displays:
    - User statistics and account status
    - System health metrics
    - Security insights
    - Recent logs and activities
    - Error monitoring
    - System resource utilization
    """
    if request.user.role != 'Admin':
        messages.error(request, _('Bạn không có quyền truy cập của quản trị viên'))
        return redirect('dashboard')
    
    today = date.today()
    
    # System users statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    
    user_by_role = User.objects.values('role').annotate(
        count=Count('id')
    ).order_by('role')
    
    # Role-based statistics
    role_stats = {
        'Admin': User.objects.filter(role='Admin').count(),
        'HR': User.objects.filter(role='HR').count(),
        'Manager': User.objects.filter(role='Manager').count(),
        'Employee': User.objects.filter(role='Employee').count(),
    }
    
    # Account status statistics
    account_status = {
        'Active': User.objects.filter(status='Active').count(),
        'Locked': User.objects.filter(status='Locked').count(),
        'Pending': User.objects.filter(status='Pending Activation').count(),
    }
    
    # Recent user activity logs
    recent_logs = SystemLog.objects.all().order_by('-timestamp')[:10]
    
    # User login activity (last 7 days)
    seven_days_ago = today - timedelta(days=7)
    
    login_logs = SystemLog.objects.filter(
        action__icontains='login', 
        timestamp__gte=seven_days_ago
    ).values('timestamp__date').annotate(
        count=Count('log_id')
    ).order_by('timestamp__date')
    
    login_dates = []
    login_counts = []
    
    # Fill in gaps and create chart data
    for i in range(7):
        log_date = seven_days_ago + timedelta(days=i)
        login_dates.append(log_date.strftime('%b %d'))
        
        # Find if we have data for this date
        day_logs = [log for log in login_logs if log['timestamp__date'] == log_date]
        if day_logs:
            login_counts.append(day_logs[0]['count'])
        else:
            login_counts.append(0)
    
    # Failed login attempts
    failed_logins = SystemLog.objects.filter(
        action__icontains='failed login',
        timestamp__gte=seven_days_ago
    ).count()
    
    # Permission distribution
    permission_stats = Permission.objects.values('module').annotate(
        count=Count('permission_id')
    ).order_by('-count')
    
    # System health metrics
    # These would typically come from a monitoring system
    # For demonstration, we'll use sample data
    system_health = {
        'database_size': '1.2 GB',
        'total_tables': '26',
        'total_records': Employee.objects.count() + Attendance.objects.count() + LeaveRequest.objects.count(),
        'disk_usage': '45%',
        'memory_usage': '32%',
        'cpu_usage': '28%',
        'uptime': '23 days, 4 hours',
        'last_backup': (today - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    # Resource utilization over time (sample data)
    resource_dates = []
    cpu_usage = []
    memory_usage = []
    disk_usage = []
    
    # Generate sample data for the last 7 days
    for i in range(7):
        sample_date = seven_days_ago + timedelta(days=i)
        resource_dates.append(sample_date.strftime('%b %d'))
        
        # Generate somewhat realistic fluctuating values
        base_cpu = 25 + (i % 3) * 5  # Base value that increases every 3 days
        base_memory = 30 + (i % 2) * 3  # Base value that increases every 2 days
        base_disk = 43 + (i / 7)  # Slowly increasing disk usage
        
        # Add randomness
        cpu_usage.append(base_cpu + random.randint(-5, 8))
        memory_usage.append(base_memory + random.randint(-3, 5))
        disk_usage.append(base_disk + random.random() * 2)
    
    # Recent errors or warnings from system logs
    # This would normally come from server logs or a specialized logging service
    recent_errors = [
        {'time': '2023-10-15 08:45:23', 'level': 'ERROR', 'message': 'Database connection timeout'},
        {'time': '2023-10-14 16:32:11', 'level': 'WARNING', 'message': 'High memory usage detected'},
        {'time': '2023-10-13 12:19:45', 'level': 'ERROR', 'message': 'Failed to send email notifications'},
        {'time': '2023-10-10 09:05:17', 'level': 'WARNING', 'message': 'Slow query performance on employee table'},
    ]
    
    # User activity heatmap by hour (sample data)
    activity_hours = list(range(0, 24))
    activity_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    # Create a 2D array representing activity level by day and hour
    # Values range from 0-100 representing activity intensity
    activity_heatmap = []
    
    for day in range(7):
        day_data = []
        for hour in range(24):
            # Working hours have higher activity
            if 8 <= hour <= 17 and day < 5:  # Weekdays 8am-5pm
                base_value = 50 + random.randint(0, 50)  # Higher activity
            elif 6 <= hour <= 19 and day < 5:  # Extended working hours on weekdays
                base_value = 20 + random.randint(0, 30)  # Medium activity
            elif day >= 5:  # Weekend
                base_value = random.randint(0, 15)  # Low activity
            else:
                base_value = random.randint(0, 10)  # Very low activity
            
            day_data.append(base_value)
        activity_heatmap.append(day_data)
    
    # Pending tasks requiring admin attention
    pending_admin_tasks = [
        {'title': 'Database backup verification', 'due_date': today + timedelta(days=1)},
        {'title': 'User permissions audit', 'due_date': today + timedelta(days=3)},
        {'title': 'System update scheduling', 'due_date': today + timedelta(days=7)},
    ]
    
    context = {
        'today': today,
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': total_users - active_users,
        'user_by_role': user_by_role,
        'role_stats': role_stats,
        'account_status': account_status,
        'recent_logs': recent_logs,
        'failed_logins': failed_logins,
        'permission_stats': permission_stats,
        'system_health': system_health,
        'recent_errors': recent_errors,
        'pending_admin_tasks': pending_admin_tasks,
        
        # Chart data
        'login_dates_json': json.dumps(login_dates),
        'login_counts_json': json.dumps(login_counts),
        
        'resource_dates_json': json.dumps(resource_dates),
        'cpu_usage_json': json.dumps(cpu_usage),
        'memory_usage_json': json.dumps(memory_usage),
        'disk_usage_json': json.dumps(disk_usage),
        
        'activity_hours_json': json.dumps(activity_hours),
        'activity_days_json': json.dumps(activity_days),
        'activity_heatmap_json': json.dumps(activity_heatmap),
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
def employee_edit_profile(request):
    """Allow employee to edit personal information"""
    if not request.user.employee:
        # Create a new employee record linked to the user
        if request.method == 'POST':
            form = EmployeeBasicInfoForm(request.POST, request.FILES)
            if form.is_valid():
                employee = form.save(commit=False)
                employee.status = 'Working'
                employee.save()
                
                # Link to user
                request.user.employee = employee
                request.user.save()
                
                messages.success(request, _('Hồ sơ đã được tạo thành công'))
                return redirect('employee_dashboard')
        else:
            # Pre-populate with user data
            initial_data = {
                'full_name': f"{request.user.first_name} {request.user.last_name}",
                'email': request.user.email
            }
            form = EmployeeBasicInfoForm(initial=initial_data)
        
        return render(request, 'employee/create_employee.html', {'form': form})
    
    # Update existing employee profile
    employee = request.user.employee
    
    if request.method == 'POST':
        form = EmployeeProfileForm(request.POST, request.FILES, instance=employee)
        location_form = EmployeeLocationForm(request.POST, instance=getattr(employee, 'employeelocation', None))
        
        if form.is_valid() and location_form.is_valid():
            employee = form.save()
            
            # Handle location data
            location = location_form.save(commit=False)
            if not hasattr(employee, 'employeelocation'):
                location.employee = employee
            location.save()
            
            messages.success(request, _('Hồ sơ đã được cập nhật thành công'))
            return redirect('employee_dashboard')
    else:
        form = EmployeeProfileForm(instance=employee)
        location_form = EmployeeLocationForm(instance=getattr(employee, 'employeelocation', None))
    
    return render(request, 'dashboard/edit_profile.html', {
        'form': form,
        'location_form': location_form,
        'employee': employee
    })


@login_required
def calendar_view(request):
    """View for calendar showing attendance and leave"""
    return render(request, 'dashboard/calendar.html')


@login_required
def calendar_data(request):
    """API endpoint to get calendar data for attendance and leave"""
    # Get date range from request
    start_date = request.GET.get('start', '')
    end_date = request.GET.get('end', '')
    view_type = request.GET.get('view', 'personal')  # personal, department, company
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        # Default to current month if dates are invalid
        today = datetime.now().date()
        start_date = today.replace(day=1)
        _, last_day = calendar.monthrange(today.year, today.month)
        end_date = today.replace(day=last_day)
    
    events = []
    
    # Handle personal view (logged in user data)
    if view_type == 'personal':
        if not request.user.employee:
            return JsonResponse({'events': []})
        
        employee = request.user.employee
        
        # Get attendance data
        attendance_records = Attendance.objects.filter(
            employee=employee,
            work_date__gte=start_date,
            work_date__lte=end_date
        )
        
        for record in attendance_records:
            # Set color based on status
            color = '#28a745'  # green for present
            if record.status == 'Absent':
                color = '#dc3545'  # red for absent
            elif record.status == 'On Leave':
                color = '#ffc107'  # yellow for leave
            elif record.status == 'Holiday':
                color = '#17a2b8'  # cyan for holiday
            elif record.status == 'Business Trip':
                color = '#6610f2'  # purple for business trip
            
            events.append({
                'id': f'attendance-{record.attendance_id}',
                'title': f'Attendance: {record.status}',
                'start': record.work_date.strftime('%Y-%m-%d'),
                'color': color,
                'type': 'attendance',
                'status': record.status,
                'time_in': record.time_in.strftime('%H:%M') if record.time_in else None,
                'time_out': record.time_out.strftime('%H:%M') if record.time_out else None,
                'allDay': True
            })
        
        # Get leave data
        leave_records = LeaveRequest.objects.filter(
            employee=employee,
            status='Approved',
            start_date__lte=end_date,
            end_date__gte=start_date
        )
        
        for leave in leave_records:
            # Leave requests can span multiple days
            current_date = max(leave.start_date, start_date)
            end_leave_date = min(leave.end_date, end_date)
            
            while current_date <= end_leave_date:
                # Skip weekends (optional)
                if current_date.weekday() < 5:  # 0-4 is Monday-Friday
                    events.append({
                        'id': f'leave-{leave.request_id}-{current_date}',
                        'title': f'Leave: {leave.leave_type}',
                        'start': current_date.strftime('%Y-%m-%d'),
                        'color': '#6f42c1',  # purple for leave
                        'type': 'leave',
                        'leave_type': leave.leave_type,
                        'allDay': True
                    })
                current_date += timedelta(days=1)
                
        # Add upcoming training
        training_records = TrainingParticipation.objects.filter(
            employee=employee,
            course__start_date__gte=start_date,
            course__start_date__lte=end_date
        ).select_related('course')
        
        for training in training_records:
            events.append({
                'id': f'training-{training.participation_id}',
                'title': f'Training: {training.course.course_name}',
                'start': training.course.start_date.strftime('%Y-%m-%d'),
                'end': (training.course.end_date or training.course.start_date).strftime('%Y-%m-%d'),
                'color': '#20c997',  # teal for training
                'type': 'training',
                'status': training.status,
                'allDay': True
            })
    
    # Handle department view (manager and above)
    elif view_type == 'department' and request.user.role in ['Manager', 'HR', 'Admin']:
        if not request.user.employee or not request.user.employee.department:
            return JsonResponse({'events': []})
        
        department = request.user.employee.department
        
        # Get all employees in department
        employees = Employee.objects.filter(department=department, status='Working')
        
        for employee in employees:
            # Get leave data for calendar
            leave_records = LeaveRequest.objects.filter(
                employee=employee,
                status='Approved',
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            
            for leave in leave_records:
                current_date = max(leave.start_date, start_date)
                end_leave_date = min(leave.end_date, end_date)
                
                while current_date <= end_leave_date:
                    if current_date.weekday() < 5:  # Skip weekends
                        events.append({
                            'id': f'leave-{leave.request_id}-{current_date}',
                            'title': f'{employee.full_name}: {leave.leave_type}',
                            'start': current_date.strftime('%Y-%m-%d'),
                            'color': '#6f42c1',  # purple for leave
                            'type': 'leave',
                            'employee': employee.full_name,
                            'leave_type': leave.leave_type,
                            'allDay': True
                        })
                    current_date += timedelta(days=1)
            
            # Get attendance data (for absences)
            absences = Attendance.objects.filter(
                employee=employee,
                work_date__gte=start_date,
                work_date__lte=end_date,
                status='Absent'
            )
            
            for absence in absences:
                events.append({
                    'id': f'absence-{absence.attendance_id}',
                    'title': f'{employee.full_name}: Absent',
                    'start': absence.work_date.strftime('%Y-%m-%d'),
                    'color': '#dc3545',  # red for absent
                    'type': 'attendance',
                    'employee': employee.full_name,
                    'status': 'Absent',
                    'allDay': True
                })
            
            # Add business trips
            business_trips = Attendance.objects.filter(
                employee=employee,
                work_date__gte=start_date,
                work_date__lte=end_date,
                status='Business Trip'
            )
            
            for trip in business_trips:
                events.append({
                    'id': f'trip-{trip.attendance_id}',
                    'title': f'{employee.full_name}: Business Trip',
                    'start': trip.work_date.strftime('%Y-%m-%d'),
                    'color': '#6610f2',  # purple for business trip
                    'type': 'attendance',
                    'employee': employee.full_name,
                    'status': 'Business Trip',
                    'allDay': True
                })
        
        # Add department trainings
        department_trainings = TrainingCourse.objects.filter(
            department=department,
            start_date__gte=start_date,
            start_date__lte=end_date
        )
        
        for training in department_trainings:
            events.append({
                'id': f'dept-training-{training.course_id}',
                'title': f'Dept Training: {training.course_name}',
                'start': training.start_date.strftime('%Y-%m-%d'),
                'end': (training.end_date or training.start_date).strftime('%Y-%m-%d'),
                'color': '#20c997',  # teal for training
                'type': 'training',
                'allDay': True
            })
    
    # Company-wide view (HR and Admin only)
    elif view_type == 'company' and request.user.role in ['HR', 'Admin']:
        # Get all approved leave requests
        leave_records = LeaveRequest.objects.filter(
            status='Approved',
            start_date__lte=end_date,
            end_date__gte=start_date
        ).select_related('employee')
        
        for leave in leave_records:
            current_date = max(leave.start_date, start_date)
            end_leave_date = min(leave.end_date, end_date)
            
            while current_date <= end_leave_date:
                if current_date.weekday() < 5:  # Skip weekends
                    dept_name = leave.employee.department.department_name if leave.employee.department else 'No Department'
                    
                    events.append({
                        'id': f'leave-{leave.request_id}-{current_date}',
                        'title': f'{leave.employee.full_name} ({dept_name}): {leave.leave_type}',
                        'start': current_date.strftime('%Y-%m-%d'),
                        'color': '#6f42c1',  # purple for leave
                        'type': 'leave',
                        'employee': leave.employee.full_name,
                        'department': dept_name,
                        'leave_type': leave.leave_type,
                        'allDay': True
                    })
                current_date += timedelta(days=1)
        
        # Add company holidays
        # This would typically come from a Holiday table, but we'll add some examples
        holidays = [
            {'date': '2023-01-01', 'name': 'New Year\'s Day'},
            {'date': '2023-01-02', 'name': 'New Year Holiday'},
            {'date': '2023-01-23', 'name': 'Lunar New Year\'s Eve'},
            {'date': '2023-01-24', 'name': 'Lunar New Year'},
            {'date': '2023-01-25', 'name': 'Lunar New Year Holiday'},
            {'date': '2023-01-26', 'name': 'Lunar New Year Holiday'},
            {'date': '2023-04-29', 'name': 'Reunification Day'},
            {'date': '2023-04-30', 'name': 'Reunification Day Holiday'},
            {'date': '2023-05-01', 'name': 'Labor Day'},
            {'date': '2023-09-02', 'name': 'National Day'},
            {'date': '2023-09-04', 'name': 'National Day Holiday'},
            {'date': '2023-12-25', 'name': 'Christmas Day'},
        ]
        
        for holiday in holidays:
            try:
                holiday_date = datetime.strptime(holiday['date'], '%Y-%m-%d').date()
                if start_date <= holiday_date <= end_date:
                    events.append({
                        'id': f'holiday-{holiday["date"]}',
                        'title': f'Holiday: {holiday["name"]}',
                        'start': holiday['date'],
                        'color': '#17a2b8',  # cyan for holiday
                        'type': 'holiday',
                        'allDay': True
                    })
            except ValueError:
                continue
        
        # Add company-wide trainings
        company_trainings = TrainingCourse.objects.filter(
            department__isnull=True,  # No specific department = company-wide
            start_date__gte=start_date,
            start_date__lte=end_date
        )
        
        for training in company_trainings:
            events.append({
                'id': f'company-training-{training.course_id}',
                'title': f'Company Training: {training.course_name}',
                'start': training.start_date.strftime('%Y-%m-%d'),
                'end': (training.end_date or training.start_date).strftime('%Y-%m-%d'),
                'color': '#20c997',  # teal for training
                'type': 'training',
                'allDay': True
            })
    
    return JsonResponse({'events': events})


# Additional widget views for dashboard components
@login_required
def attendance_widget(request):
    """API endpoint to get attendance widget data"""
    if not request.user.employee:
        return JsonResponse({'error': 'Không tìm thấy hồ sơ nhân viên'})
    
    employee = request.user.employee
    today = date.today()
    month_start = today.replace(day=1)
    
    # Get monthly attendance summary
    attendance_stats = Attendance.objects.filter(
        employee=employee,
        work_date__gte=month_start,
        work_date__lte=today
    ).aggregate(
        total=Count('attendance_id'),
        present=Count('attendance_id', filter=Q(status='Present')),
        absent=Count('attendance_id', filter=Q(status='Absent')),
        on_leave=Count('attendance_id', filter=Q(status='On Leave')),
    )
    
    # Get today's attendance
    today_attendance = Attendance.objects.filter(
        employee=employee,
        work_date=today
    ).first()
    
    today_status = None
    if today_attendance:
        today_status = {
            'status': today_attendance.status,
            'time_in': today_attendance.time_in.strftime('%H:%M:%S') if today_attendance.time_in else None,
            'time_out': today_attendance.time_out.strftime('%H:%M:%S') if today_attendance.time_out else None,
        }
    
    return JsonResponse({
        'stats': attendance_stats,
        'today': today_status
    })


@login_required
def leave_widget(request):
    """API endpoint to get leave widget data"""
    if not request.user.employee:
        return JsonResponse({'error': 'Không tìm thấy hồ sơ nhân viên'})
    
    employee = request.user.employee
    today = date.today()
    
    # Get pending leave requests
    pending_leaves = LeaveRequest.objects.filter(
        employee=employee,
        status='Pending'
    ).order_by('-start_date')[:3]
    
    pending_data = []
    for leave in pending_leaves:
        pending_data.append({
            'id': leave.request_id,
            'leave_type': leave.leave_type,
            'start_date': leave.start_date.strftime('%Y-%m-%d'),
            'end_date': leave.end_date.strftime('%Y-%m-%d'),
            'leave_days': float(leave.leave_days),
            'status': leave.status,
            'created_date': leave.created_date.strftime('%Y-%m-%d'),
        })
    
    # Get leave balances
    leave_balances = LeaveBalance.objects.filter(
        employee=employee,
        year=today.year
    )
    
    balance_data = {}
    for balance in leave_balances:
        balance_data[balance.leave_type] = {
            'total': float(balance.total_days),
            'used': float(balance.used_days),
            'remaining': float(balance.remaining_days),
        }
    
    return JsonResponse({
        'pending': pending_data,
        'balances': balance_data
    })


@login_required
def tasks_widget(request):
    """API endpoint to get tasks widget data"""
    if not request.user.employee:
        return JsonResponse({'error': 'Không tìm thấy hồ sơ nhân viên'})
    
    employee = request.user.employee
    today = date.today()
    
    # Get tasks assigned to employee
    tasks = Task.objects.filter(assignee=employee)
    
    # Calculate task statistics
    task_stats = tasks.aggregate(
        total=Count('task_id'),
        not_started=Count('task_id', filter=Q(status='Not Started')),
        in_progress=Count('task_id', filter=Q(status='In Progress')),
        completed=Count('task_id', filter=Q(status='Completed')),
        on_hold=Count('task_id', filter=Q(status='On Hold')),
    )
    
    # Add overdue count
    task_stats['overdue'] = tasks.filter(
        status__in=['Not Started', 'In Progress', 'On Hold'],
        due_date__lt=today
    ).count()
    
    # Get upcoming tasks
    upcoming_tasks = tasks.filter(
        status__in=['Not Started', 'In Progress'],
        due_date__gte=today
    ).order_by('due_date')[:5]
    
    upcoming_data = []
    for task in upcoming_tasks:
        upcoming_data.append({
            'id': task.task_id,
            'title': task.title,
            'status': task.status,
            'priority': task.priority,
            'due_date': task.due_date.strftime('%Y-%m-%d'),
            'progress': task.progress,
            'days_left': (task.due_date - today).days,
        })
    
    return JsonResponse({
        'stats': task_stats,
        'upcoming': upcoming_data
    })


@login_required
def announcements_widget(request):
    """API endpoint to get announcements widget data"""
    # In a real system, you would have an Announcements model
    # Here we'll return sample data
    announcements = [
        {
            'id': 1,
            'title': 'Company Picnic',
            'content': 'Annual company picnic will be held next month. Please RSVP by the end of this week.',
            'date': (date.today() + timedelta(days=15)).strftime('%Y-%m-%d'),
            'is_important': True
        },
        {
            'id': 2,
            'title': 'New Benefits Package',
            'content': 'HR has announced updates to our benefits package. Check your email for details.',
            'date': (date.today() - timedelta(days=2)).strftime('%Y-%m-%d'),
            'is_important': True
        },
        {
            'id': 3,
            'title': 'Office Maintenance',
            'content': 'The office will be closed this Saturday for scheduled maintenance.',
            'date': (date.today() + timedelta(days=3)).strftime('%Y-%m-%d'),
            'is_important': False
        }
    ]
    
    return JsonResponse({
        'announcements': announcements
    })


@login_required
def birthday_widget(request):
    """API endpoint to get upcoming birthdays widget data"""
    # This function would show upcoming employee birthdays
    today = date.today()
    upcoming_days = 30  # Show birthdays in the next 30 days
    
    birthdays = []
    employees = Employee.objects.filter(date_of_birth__isnull=False, status='Working')
    
    for employee in employees:
        birth_date = employee.date_of_birth
        
        # Calculate next birthday
        next_birthday = date(today.year, birth_date.month, birth_date.day)
        if next_birthday < today:
            next_birthday = date(today.year + 1, birth_date.month, birth_date.day)
        
        # Check if birthday is within the next X days
        days_until = (next_birthday - today).days
        if days_until <= upcoming_days:
            age = next_birthday.year - birth_date.year
            
            birthdays.append({
                'id': employee.employee_id,
                'name': employee.full_name,
                'position': employee.position.position_name if employee.position else '',
                'department': employee.department.department_name if employee.department else '',
                'birth_date': birth_date.strftime('%Y-%m-%d'),
                'next_birthday': next_birthday.strftime('%Y-%m-%d'),
                'days_until': days_until,
                'age': age,
                'image': employee.profile_image.url if employee.profile_image else None
            })
    
    # Sort by days until birthday
    birthdays.sort(key=lambda x: x['days_until'])
    
    return JsonResponse({
        'birthdays': birthdays[:10]  # Limit to 10 entries
    })
