from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count, Sum, Q
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import date, datetime, timedelta
import csv
import io
import xlsxwriter
import json
import calendar
from .models import KPI, EmployeeEvaluation, RewardsAndDisciplinary
from .forms import KPIForm, EmployeeEvaluationForm, RewardsAndDisciplinaryForm, PerformanceReviewForm
from employee.models import Employee, Department
from accounts.decorators import *
from notifications.services import create_notification

@login_required
@check_module_permission('performance', 'View')
def kpi_list(request):
    """List all KPIs"""
    kpis = KPI.objects.all().order_by('kpi_type', 'kpi_name')
    
    kpi_type_filter = request.GET.get('type', '')
    if kpi_type_filter:
        kpis = kpis.filter(kpi_type=kpi_type_filter)
    
    return render(request, 'performance/kpi_list.html', {
        'kpis': kpis,
        'kpi_type_filter': kpi_type_filter
    })

@login_required
@hr_required
def kpi_create(request):
    """Create a new KPI"""
    if request.method == 'POST':
        form = KPIForm(request.POST)
        if form.is_valid():
            kpi = form.save()
            messages.success(request, f"KPI '{kpi.kpi_name}' created successfully")
            return redirect('kpi_list')
    else:
        form = KPIForm()
    
    return render(request, 'performance/kpi_form.html', {
        'form': form,
        'title': 'Create New KPI',
        'submit_text': 'Create KPI'
    })

@login_required
@hr_required
def kpi_update(request, pk):
    """Update an existing KPI"""
    kpi = get_object_or_404(KPI, pk=pk)
    
    if request.method == 'POST':
        form = KPIForm(request.POST, instance=kpi)
        if form.is_valid():
            form.save()
            messages.success(request, f"KPI '{kpi.kpi_name}' updated successfully")
            return redirect('kpi_list')
    else:
        form = KPIForm(instance=kpi)
    
    return render(request, 'performance/kpi_form.html', {
        'form': form,
        'kpi': kpi,
        'title': f"Edit KPI: {kpi.kpi_name}",
        'submit_text': 'Update KPI'
    })

@login_required
@hr_required
def kpi_delete(request, pk):
    """Delete a KPI"""
    kpi = get_object_or_404(KPI, pk=pk)
    kpi_name = kpi.kpi_name
    
    if request.method == 'POST':
        # Check if KPI is in use
        in_use = EmployeeEvaluation.objects.filter(kpi=kpi).exists()
        if in_use:
            messages.error(request, f"Cannot delete '{kpi_name}' because it's being used in evaluations")
            return redirect('kpi_list')
        
        kpi.delete()
        messages.success(request, f"KPI '{kpi_name}' deleted successfully")
        return redirect('kpi_list')
    
    return render(request, 'performance/kpi_confirm_delete.html', {
        'kpi': kpi
    })

@login_required
@manager_required
def evaluate_employee(request, employee_id):
    """Create performance evaluation for an employee"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    # Check if manager has permission to evaluate this employee
    is_hr_or_admin = request.user.role in ['HR', 'Admin']
    is_department_manager = (request.user.role == 'Manager' and 
                           request.user.employee and request.user.employee.department == employee.department)
    
    if not (is_hr_or_admin or is_department_manager):
        messages.error(request, 'You do not have permission to evaluate this employee')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = EmployeeEvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.employee = employee
            evaluation.evaluated_by = request.user.employee
            evaluation.evaluation_date = date.today()
            evaluation.save()
            
            # Notify employee about new evaluation
            from django.contrib.auth import get_user_model
            User = get_user_model()
            employee_user = User.objects.filter(employee=employee).first()
            if employee_user:
                create_notification(
                    user=employee_user,
                    notification_type='Performance',
                    title='New Performance Evaluation',
                    message=f'A new evaluation for {calendar.month_name[evaluation.month]} {evaluation.year} has been submitted.',
                    link=f'/performance/employee/{employee.employee_id}/evaluations/'
                )
            
            messages.success(request, 'Evaluation submitted successfully')
            return redirect('employee_evaluations', employee_id=employee_id)
    else:
        # Get current month and year as default
        current_month = date.today().month
        current_year = date.today().year
        
        # Set initial values based on KPI targets
        initial_data = {
            'month': current_month,
            'year': current_year
        }
        
        form = EmployeeEvaluationForm(initial=initial_data)
        
        # Filter KPIs based on employee's department and individual KPIs
        if employee.department:
            form.fields['kpi'].queryset = KPI.objects.filter(
                Q(kpi_type='Individual') | 
                Q(kpi_type='Department') | 
                Q(kpi_type='Company')
            )
        else:
            form.fields['kpi'].queryset = KPI.objects.filter(
                Q(kpi_type='Individual') | 
                Q(kpi_type='Company')
            )
    
    # Get recent evaluations for context
    recent_evaluations = EmployeeEvaluation.objects.filter(
        employee=employee
    ).order_by('-year', '-month', 'kpi__kpi_name')[:5]
    
    return render(request, 'performance/evaluation_form.html', {
        'form': form,
        'employee': employee,
        'recent_evaluations': recent_evaluations
    })

@login_required
def evaluation_detail(request, pk):
    """View details of a specific evaluation"""
    evaluation = get_object_or_404(EmployeeEvaluation, pk=pk)
    
    # Check permissions
    is_owner = request.user.employee == evaluation.employee
    is_evaluator = request.user.employee == evaluation.evaluated_by
    is_manager = (request.user.role == 'Manager' and request.user.employee and 
                  evaluation.employee.department == request.user.employee.department)
    is_hr_admin = request.user.role in ['HR', 'Admin']
    
    if not (is_owner or is_evaluator or is_manager or is_hr_admin):
        messages.error(request, "You don't have permission to view this evaluation")
        return redirect('dashboard')
    
    return render(request, 'performance/evaluation_detail.html', {
        'evaluation': evaluation,
        'can_edit': is_evaluator or is_hr_admin
    })

@login_required
@check_module_permission('performance', 'Edit')
def evaluation_update(request, pk):
    """Update an existing evaluation"""
    evaluation = get_object_or_404(EmployeeEvaluation, pk=pk)
    
    # Check edit permissions
    is_evaluator = request.user.employee == evaluation.evaluated_by
    is_hr_admin = request.user.role in ['HR', 'Admin']
    
    if not (is_evaluator or is_hr_admin):
        messages.error(request, "You don't have permission to edit this evaluation")
        return redirect('evaluation_detail', pk=pk)
    
    if request.method == 'POST':
        form = EmployeeEvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            form.save()
            messages.success(request, "Evaluation updated successfully")
            return redirect('evaluation_detail', pk=pk)
    else:
        form = EmployeeEvaluationForm(instance=evaluation)
    
    return render(request, 'performance/evaluation_form.html', {
        'form': form,
        'employee': evaluation.employee,
        'evaluation': evaluation,
        'is_update': True
    })

@login_required
@check_module_permission('performance', 'View')
def employee_evaluations(request, employee_id):
    """View evaluation history for an employee"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    # Check permissions
    is_owner = request.user.employee == employee
    is_manager = (request.user.role == 'Manager' and request.user.employee and 
                  employee.department == request.user.employee.department)
    is_hr_admin = request.user.role in ['HR', 'Admin']
    
    if not (is_owner or is_manager or is_hr_admin):
        messages.error(request, "You don't have permission to view this employee's evaluations")
        return redirect('dashboard')
    
    year_filter = request.GET.get('year', date.today().year)
    month_filter = request.GET.get('month', '')
    
    try:
        year_filter = int(year_filter)
    except ValueError:
        year_filter = date.today().year
    
    evaluations = EmployeeEvaluation.objects.filter(
        employee=employee,
        year=year_filter
    ).order_by('-month', 'kpi__kpi_name')
    
    if month_filter:
        try:
            month_filter = int(month_filter)
            evaluations = evaluations.filter(month=month_filter)
        except ValueError:
            pass
    
    # Calculate average achievement rate
    avg_achievement = evaluations.aggregate(avg=Avg('achievement_rate'))['avg'] or 0
    
    # Get available years for filter
    available_years = EmployeeEvaluation.objects.filter(
        employee=employee
    ).values_list('year', flat=True).distinct().order_by('-year')
    
    # Group evaluations by month
    evaluations_by_month = {}
    for eval in evaluations:
        month_key = f"{eval.month}-{eval.year}"
        if month_key not in evaluations_by_month:
            evaluations_by_month[month_key] = {
                'month_name': calendar.month_name[eval.month],
                'year': eval.year,
                'month': eval.month,
                'evaluations': [],
                'avg_achievement': 0,
                'total_evaluations': 0
            }
        evaluations_by_month[month_key]['evaluations'].append(eval)
        evaluations_by_month[month_key]['total_evaluations'] += 1
    
    # Calculate average for each month
    for month_key, data in evaluations_by_month.items():
        total_achievement = sum(eval.achievement_rate or 0 for eval in data['evaluations'])
        if data['total_evaluations'] > 0:
            data['avg_achievement'] = total_achievement / data['total_evaluations']
    
    # Sort by month (descending)
    evaluations_by_month = dict(sorted(
        evaluations_by_month.items(), 
        key=lambda x: (x[1]['year'], x[1]['month']),
        reverse=True
    ))
    
    return render(request, 'performance/employee_evaluations.html', {
        'employee': employee,
        'evaluations_by_month': evaluations_by_month,
        'avg_achievement': avg_achievement,
        'year_filter': year_filter,
        'month_filter': month_filter,
        'available_years': available_years,
        'can_evaluate': is_manager or is_hr_admin
    })

@login_required
@employee_approved_required
def my_performance(request):
    """View my performance evaluations"""
    if not request.user.employee:
        messages.error(request, "You don't have an employee profile")
        return redirect('dashboard')
    
    return redirect('employee_evaluations', employee_id=request.user.employee.employee_id)

@login_required
def self_evaluation(request):
    """Submit a self-evaluation"""
    if not request.user.employee:
        messages.error(request, "You don't have an employee profile")
        return redirect('dashboard')
    
    employee = request.user.employee
    
    if request.method == 'POST':
        form = EmployeeEvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.employee = employee
            evaluation.evaluated_by = employee  # Self-evaluation
            evaluation.evaluation_date = date.today()
            evaluation.save()
            
            # Notify manager about new self-evaluation
            if employee.department:
                # Find manager
                from django.contrib.auth import get_user_model
                User = get_user_model()
                managers = User.objects.filter(
                    role='Manager',
                    employee__department=employee.department,
                    is_active=True
                )
                
                for manager in managers:
                    create_notification(
                        user=manager,
                        notification_type='Performance',
                        title='New Self-Evaluation',
                        message=f'{employee.full_name} has submitted a self-evaluation for {calendar.month_name[evaluation.month]} {evaluation.year}.',
                        link=f'/performance/evaluation/{evaluation.evaluation_id}/'
                    )
            
            messages.success(request, 'Self-evaluation submitted successfully')
            return redirect('my_performance')
    else:
        # Get current month and year as default
        current_month = date.today().month
        current_year = date.today().year
        
        initial_data = {
            'month': current_month,
            'year': current_year
        }
        
        form = EmployeeEvaluationForm(initial=initial_data)
        
        # Filter KPIs relevant to the employee
        if employee.department:
            form.fields['kpi'].queryset = KPI.objects.filter(
                Q(kpi_type='Individual') | 
                (Q(kpi_type='Department') & Q(department=employee.department)) | 
                Q(kpi_type='Company')
            )
        else:
            form.fields['kpi'].queryset = KPI.objects.filter(
                Q(kpi_type='Individual') | Q(kpi_type='Company')
            )
    
    return render(request, 'performance/self_evaluation_form.html', {
        'form': form,
        'employee': employee
    })

@login_required
@manager_required
def team_performance(request):
    """View performance of team members"""
    if not request.user.employee or not request.user.employee.department:
        messages.error(request, "You don't have a department assigned")
        return redirect('dashboard')
    
    department = request.user.employee.department
    year_filter = request.GET.get('year', date.today().year)
    
    try:
        year_filter = int(year_filter)
    except ValueError:
        year_filter = date.today().year
    
    # Get team members
    team_members = Employee.objects.filter(
        department=department,
        status='Working'
    ).exclude(pk=request.user.employee.pk)
    
    # Get performance data for each team member
    team_performance = []
    for member in team_members:
        evaluations = EmployeeEvaluation.objects.filter(
            employee=member,
            year=year_filter
        )
        
        avg_achievement = evaluations.aggregate(avg=Avg('achievement_rate'))['avg'] or 0
        evaluation_count = evaluations.count()
        
        # Get monthly averages
        monthly_data = {}
        for month in range(1, 13):
            month_evals = evaluations.filter(month=month)
            month_avg = month_evals.aggregate(avg=Avg('achievement_rate'))['avg'] or 0
            month_count = month_evals.count()
            
            monthly_data[month] = {
                'avg': month_avg,
                'count': month_count
            }
        
        team_performance.append({
            'employee': member,
            'avg_achievement': avg_achievement,
            'evaluation_count': evaluation_count,
            'monthly_data': monthly_data
        })
    
    # Sort by average achievement (descending)
    team_performance.sort(key=lambda x: x['avg_achievement'], reverse=True)
    
    # Get available years for filter
    available_years = EmployeeEvaluation.objects.filter(
        employee__department=department
    ).values_list('year', flat=True).distinct().order_by('-year')
    
    return render(request, 'performance/team_performance.html', {
        'department': department,
        'team_performance': team_performance,
        'year_filter': year_filter,
        'available_years': available_years,
        'months': [{'number': i, 'name': calendar.month_name[i]} for i in range(1, 13)]
    })

@login_required
@check_module_permission('performance', 'View')
def department_performance(request, department_id=None):
    """View performance dashboard for a department"""
    # If department_id is not provided and user is a manager, use their department
    if department_id is None and request.user.role == 'Manager' and request.user.employee and request.user.employee.department:
        department_id = request.user.employee.department.department_id
    
    department = None
    if department_id:
        department = get_object_or_404(Department, pk=department_id)
    
    # Get filters
    year_filter = request.GET.get('year', date.today().year)
    try:
        year_filter = int(year_filter)
    except ValueError:
        year_filter = date.today().year
    
    # For HR and Admin, they can see all departments
    if department:
        departments = [department]
    elif request.user.role in ['HR', 'Admin']:
        departments = Department.objects.filter(status=1)
    else:
        messages.error(request, "Please select a department")
        return redirect('dashboard')
    
    # Aggregated performance data
    aggregated_data = []
    for dept in departments:
        # Get all evaluations for this department in the selected year
        dept_evaluations = EmployeeEvaluation.objects.filter(
            employee__department=dept,
            year=year_filter
        )
        
        avg_achievement = dept_evaluations.aggregate(avg=Avg('achievement_rate'))['avg'] or 0
        employee_count = Employee.objects.filter(department=dept, status='Working').count()
        evaluation_count = dept_evaluations.count()
        
        # Monthly averages for chart
        monthly_avgs = []
        for month in range(1, 13):
            month_evals = dept_evaluations.filter(month=month)
            month_avg = month_evals.aggregate(avg=Avg('achievement_rate'))['avg'] or 0
            monthly_avgs.append(round(month_avg, 2))
        
        # Top performers
        top_performers = []
        employees = Employee.objects.filter(department=dept, status='Working')
        for emp in employees:
            emp_evals = dept_evaluations.filter(employee=emp)
            emp_avg = emp_evals.aggregate(avg=Avg('achievement_rate'))['avg'] or 0
            if emp_avg > 0:  # Only include employees with evaluations
                top_performers.append({
                    'employee': emp,
                    'avg_achievement': emp_avg,
                    'evaluation_count': emp_evals.count()
                })
        
        # Sort and limit to top 5
        top_performers.sort(key=lambda x: x['avg_achievement'], reverse=True)
        top_performers = top_performers[:5]
        
        aggregated_data.append({
            'department': dept,
            'avg_achievement': avg_achievement,
            'employee_count': employee_count,
            'evaluation_count': evaluation_count,
            'monthly_avgs': monthly_avgs,
            'top_performers': top_performers
        })
    
    # Get available years for filter
    available_years = EmployeeEvaluation.objects.values_list('year', flat=True).distinct().order_by('-year')
    
    # Get all departments for department selection
    all_departments = Department.objects.filter(status=1)
    
    return render(request, 'performance/department_performance.html', {
        'aggregated_data': aggregated_data,
        'selected_department': department,
        'all_departments': all_departments,
        'year_filter': year_filter,
        'available_years': available_years,
        'months': [calendar.month_name[i] for i in range(1, 13)]
    })

@login_required
@check_module_permission('performance', 'View')
def performance_evaluations(request):
    """HR/Admin view of all evaluations"""
    # Filters
    employee_filter = request.GET.get('employee', '')
    department_filter = request.GET.get('department', '')
    year_filter = request.GET.get('year', date.today().year)
    month_filter = request.GET.get('month', '')
    
    try:
        year_filter = int(year_filter)
    except ValueError:
        year_filter = date.today().year
    
    # Base query
    evaluations = EmployeeEvaluation.objects.all().select_related(
        'employee', 'employee__department', 'kpi', 'evaluated_by'
    )
    
    # Apply filters
    if employee_filter:
        evaluations = evaluations.filter(employee_id=employee_filter)
    
    if department_filter:
        evaluations = evaluations.filter(employee__department_id=department_filter)
    
    evaluations = evaluations.filter(year=year_filter)
    
    if month_filter:
        try:
            month_filter = int(month_filter)
            evaluations = evaluations.filter(month=month_filter)
        except ValueError:
            pass
    
    # Order by most recent
    evaluations = evaluations.order_by('-year', '-month', 'employee__full_name')
    
    # Paginate results
    paginator = Paginator(evaluations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get data for filters
    departments = Department.objects.filter(status=1)
    employees = Employee.objects.filter(status='Working').order_by('full_name')
    
    # Get available years for filter
    available_years = EmployeeEvaluation.objects.values_list('year', flat=True).distinct().order_by('-year')
    
    return render(request, 'performance/performance_evaluations.html', {
        'page_obj': page_obj,
        'departments': departments,
        'employees': employees,
        'employee_filter': employee_filter,
        'department_filter': department_filter,
        'year_filter': year_filter,
        'month_filter': month_filter,
        'available_years': available_years
    })

@login_required
@check_module_permission('performance', 'View')
def performance_report(request):
    """Generate performance reports"""
    if request.method == 'POST':
        form = PerformanceReviewForm(request.POST)
        if form.is_valid():
            department = form.cleaned_data['department']
            month = form.cleaned_data['month']
            year = form.cleaned_data['year']
            review_deadline = form.cleaned_data['review_deadline']
            
            # Create review cycle and notify managers
            if department:
                # Specific department review
                departments = [department]
            else:
                # Company-wide review
                departments = Department.objects.filter(status=1)
            
            for dept in departments:
                # Notify department manager(s)
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                managers = User.objects.filter(
                    role='Manager',
                    employee__department=dept,
                    is_active=True
                )
                
                for manager in managers:
                    create_notification(
                        user=manager,
                        notification_type='Performance',
                        title='Performance Review Cycle Started',
                        message=f'Please complete performance reviews for your team for {calendar.month_name[int(month)]} {year} by {review_deadline}.',
                        link=f'/performance/team/'
                    )
            
            messages.success(request, f'Performance review cycle initiated for {calendar.month_name[int(month)]} {year}')
            return redirect('performance_evaluations')
    else:
        form = PerformanceReviewForm()
    
    # Generate summary statistics
    current_year = date.today().year
    departments = Department.objects.filter(status=1)
    
    department_stats = []
    for dept in departments:
        # Evaluations this year
        dept_evals = EmployeeEvaluation.objects.filter(
            employee__department=dept,
            year=current_year
        )
        
        total_evals = dept_evals.count()
        avg_achievement = dept_evals.aggregate(avg=Avg('achievement_rate'))['avg'] or 0
        
        # Employees with and without evaluations
        employees = Employee.objects.filter(department=dept, status='Working')
        total_employees = employees.count()
        
        evaluated_employees = dept_evals.values('employee').distinct().count()
        missing_evaluations = total_employees - evaluated_employees
        
        department_stats.append({
            'department': dept,
            'total_evaluations': total_evals,
            'avg_achievement': avg_achievement,
            'total_employees': total_employees,
            'evaluated_employees': evaluated_employees,
            'missing_evaluations': missing_evaluations
        })
    
    return render(request, 'performance/performance_report.html', {
        'form': form,
        'department_stats': department_stats,
        'current_year': current_year
    })

@login_required
@hr_required
def rewards_disciplinary_list(request):
    """List all rewards and disciplinary actions"""
    # Filters
    employee_filter = request.GET.get('employee', '')
    department_filter = request.GET.get('department', '')
    type_filter = request.GET.get('type', '')
    year_filter = request.GET.get('year', '')
    
    # Base query
    actions = RewardsAndDisciplinary.objects.all().select_related(
        'employee', 'employee__department', 'decided_by'
    )
    
    # Apply filters
    if employee_filter:
        actions = actions.filter(employee_id=employee_filter)
    
    if department_filter:
        actions = actions.filter(employee__department_id=department_filter)
    
    if type_filter:
        actions = actions.filter(type=type_filter)
    
    if year_filter:
        try:
            year = int(year_filter)
            actions = actions.filter(decision_date__year=year)
        except ValueError:
            pass
    
    # Order by most recent
    actions = actions.order_by('-decision_date')
    
    # Paginate results
    paginator = Paginator(actions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get data for filters
    departments = Department.objects.filter(status=1)
    employees = Employee.objects.filter(status='Working').order_by('full_name')
    
    # Get available years for filter
    available_years = RewardsAndDisciplinary.objects.dates('decision_date', 'year', order='DESC')
    
    return render(request, 'performance/rewards_disciplinary_list.html', {
        'page_obj': page_obj,
        'departments': departments,
        'employees': employees,
        'employee_filter': employee_filter,
        'department_filter': department_filter,
        'type_filter': type_filter,
        'year_filter': year_filter,
        'available_years': available_years
    })

@login_required
@hr_required
def rewards_disciplinary_create(request):
    """Create a new reward or disciplinary action"""
    if request.method == 'POST':
        form = RewardsAndDisciplinaryForm(request.POST, request.FILES)
        if form.is_valid():
            action = form.save(commit=False)
            
            # Set decided_by if not provided
            if not action.decided_by:
                action.decided_by = request.user.employee
            
            action.save()
            
            # Notify employee
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            employee_user = User.objects.filter(employee=action.employee).first()
            if employee_user:
                create_notification(
                    user=employee_user,
                    notification_type='Performance',
                    title=f'New {action.get_type_display()} Action',
                    message=f'A new {action.get_type_display().lower()} action has been recorded for you.',
                    link=f'/performance/rewards-disciplinary/{action.rad_id}/'
                )
            
            messages.success(request, f'{action.get_type_display()} action created successfully')
            return redirect('rewards_disciplinary_list')
    else:
        # Pre-fill decided_by with current user's employee
        initial = {}
        if request.user.employee:
            initial['decided_by'] = request.user.employee
            
        form = RewardsAndDisciplinaryForm(initial=initial)
    
    return render(request, 'performance/rewards_disciplinary_form.html', {
        'form': form,
        'title': 'Create Reward/Disciplinary Action',
        'submit_text': 'Create'
    })

@login_required
@check_module_permission('performance', 'View')
def rewards_disciplinary_detail(request, pk):
    """View a reward or disciplinary action"""
    action = get_object_or_404(RewardsAndDisciplinary, pk=pk)
    
    # Check permissions
    is_owner = request.user.employee == action.employee
    is_creator = request.user.employee == action.decided_by
    is_hr_admin = request.user.role in ['HR', 'Admin']
    is_manager = (request.user.role == 'Manager' and request.user.employee and 
                  action.employee.department == request.user.employee.department)
    
    if not (is_owner or is_creator or is_manager or is_hr_admin):
        messages.error(request, "You don't have permission to view this")
        return redirect('dashboard')
    
    return render(request, 'performance/rewards_disciplinary_detail.html', {
        'action': action,
        'can_edit': is_creator or is_hr_admin
    })

@login_required
@hr_required
def rewards_disciplinary_update(request, pk):
    """Update a reward or disciplinary action"""
    action = get_object_or_404(RewardsAndDisciplinary, pk=pk)
    
    if request.method == 'POST':
        form = RewardsAndDisciplinaryForm(request.POST, request.FILES, instance=action)
        if form.is_valid():
            form.save()
            messages.success(request, f'{action.get_type_display()} action updated successfully')
            return redirect('rewards_disciplinary_detail', pk=pk)
    else:
        form = RewardsAndDisciplinaryForm(instance=action)
    
    return render(request, 'performance/rewards_disciplinary_form.html', {
        'form': form,
        'action': action,
        'title': f'Edit {action.get_type_display()} Action',
        'submit_text': 'Update'
    })

@login_required
@hr_required
def rewards_disciplinary_delete(request, pk):
    """Delete a reward or disciplinary action"""
    action = get_object_or_404(RewardsAndDisciplinary, pk=pk)
    
    if request.method == 'POST':
        action_type = action.get_type_display()
        action.delete()
        messages.success(request, f'{action_type} action deleted successfully')
        return redirect('rewards_disciplinary_list')
    
    return render(request, 'performance/rewards_disciplinary_confirm_delete.html', {
        'action': action
    })

@login_required
def my_rewards_disciplinary(request):
    """View my rewards and disciplinary actions"""
    if not request.user.employee:
        messages.error(request, "You don't have an employee profile")
        return redirect('dashboard')
    
    actions = RewardsAndDisciplinary.objects.filter(
        employee=request.user.employee
    ).order_by('-decision_date')
    
    # Split into rewards and disciplinary actions
    rewards = actions.filter(type='Reward')
    disciplinary = actions.filter(type='Disciplinary')
    
    return render(request, 'performance/my_rewards_disciplinary.html', {
        'rewards': rewards,
        'disciplinary': disciplinary
    })

@login_required
@check_module_permission('performance', 'View')
def export_performance(request):
    """Export performance data as CSV/Excel"""
    # Get filter parameters
    employee_id = request.GET.get('employee', '')
    department_id = request.GET.get('department', '')
    year = request.GET.get('year', date.today().year)
    month = request.GET.get('month', '')
    export_format = request.GET.get('format', 'csv')
    
    # Build query
    evaluations = EmployeeEvaluation.objects.select_related(
        'employee', 'employee__department', 'kpi', 'evaluated_by'
    ).filter(year=year)
    
    if employee_id:
        evaluations = evaluations.filter(employee_id=employee_id)
    
    if department_id:
        evaluations = evaluations.filter(employee__department_id=department_id)
    
    if month:
        evaluations = evaluations.filter(month=month)
    
    # Order results
    evaluations = evaluations.order_by('employee__full_name', 'month', 'kpi__kpi_name')
    
    # Generate filename
    filename_parts = ['performance']
    if employee_id:
        employee = Employee.objects.get(pk=employee_id)
        filename_parts.append(employee.full_name.replace(' ', '_'))
    elif department_id:
        department = Department.objects.get(pk=department_id)
        filename_parts.append(department.department_name.replace(' ', '_'))
    
    filename_parts.append(str(year))
    if month:
        filename_parts.append(calendar.month_name[int(month)])
    
    filename = "_".join(filename_parts)
    
    # Export as CSV
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Employee ID', 'Employee Name', 'Department', 'Position', 
            'Month', 'Year', 'KPI', 'KPI Type', 'Target', 'Result', 
            'Achievement Rate (%)', 'Evaluated By', 'Evaluation Date'
        ])
        
        for eval in evaluations:
            writer.writerow([
                eval.employee.employee_id,
                eval.employee.full_name,
                eval.employee.department.department_name if eval.employee.department else '',
                eval.employee.position.position_name if eval.employee.position else '',
                calendar.month_name[eval.month],
                eval.year,
                eval.kpi.kpi_name,
                eval.kpi.get_kpi_type_display(),
                eval.target,
                eval.result,
                eval.achievement_rate,
                eval.evaluated_by.full_name if eval.evaluated_by else '',
                eval.evaluation_date
            ])
        
        return response
    
    # Export as Excel
    elif export_format == 'excel':
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Performance Data')
        
        # Add headers with formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#3f51b5',
            'color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        headers = [
            'Employee ID', 'Employee Name', 'Department', 'Position', 
            'Month', 'Year', 'KPI', 'KPI Type', 'Target', 'Result', 
            'Achievement Rate (%)', 'Evaluated By', 'Evaluation Date'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Add data
        row = 1
        for eval in evaluations:
            worksheet.write(row, 0, eval.employee.employee_id)
            worksheet.write(row, 1, eval.employee.full_name)
            worksheet.write(row, 2, eval.employee.department.department_name if eval.employee.department else '')
            worksheet.write(row, 3, eval.employee.position.position_name if eval.employee.position else '')
            worksheet.write(row, 4, calendar.month_name[eval.month])
            worksheet.write(row, 5, eval.year)
            worksheet.write(row, 6, eval.kpi.kpi_name)
            worksheet.write(row, 7, eval.kpi.get_kpi_type_display())
            worksheet.write(row, 8, float(eval.target))
            worksheet.write(row, 9, float(eval.result))
            worksheet.write(row, 10, float(eval.achievement_rate) if eval.achievement_rate else 0)
            worksheet.write(row, 11, eval.evaluated_by.full_name if eval.evaluated_by else '')
            worksheet.write(row, 12, eval.evaluation_date.strftime('%Y-%m-%d'))
            row += 1
        
        # Auto-fit columns
        for col in range(len(headers)):
            worksheet.set_column(col, col, max(len(headers[col]) + 2, 12))
        
        workbook.close()
        
        # Prepare response
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        
        return response
    
    # If invalid format, redirect back
    messages.error(request, 'Invalid export format')
    return redirect('performance_evaluations')
