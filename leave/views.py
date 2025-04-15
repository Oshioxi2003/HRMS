from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.urls import reverse
from datetime import date, datetime, timedelta
import csv
from io import StringIO
import calendar

from .models import LeaveRequest, LeaveBalance
from .forms import LeaveRequestForm, LeaveApprovalForm, LeaveBalanceForm, DateRangeForm
from employee.models import Employee, Department
from accounts.decorators import *
from notifications.services import create_notification

# Employee Views
@login_required
@employee_approved_required
def my_leave_requests(request):
    """View employee's own leave requests"""
    if not request.user.employee:
        messages.error(request, 'You do not have an employee profile')
        return redirect('dashboard')
    
    # Filter based on status
    status_filter = request.GET.get('status', '')
    
    requests = LeaveRequest.objects.filter(employee=request.user.employee)
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    # Order by creation date (newest first)
    requests = requests.order_by('-created_date')
    
    # Get leave summary for current year
    current_year = date.today().year
    annual_leave = LeaveRequest.objects.filter(
        employee=request.user.employee,
        leave_type='Annual Leave',
        status='Approved',
        start_date__year=current_year
    ).aggregate(total=Sum('leave_days'))
    
    sick_leave = LeaveRequest.objects.filter(
        employee=request.user.employee,
        leave_type='Sick Leave',
        status='Approved',
        start_date__year=current_year
    ).aggregate(total=Sum('leave_days'))
    
    leave_summary = {
        'annual': annual_leave['total'] or 0,
        'sick': sick_leave['total'] or 0
    }
    
    return render(request, 'leave/my_leave_requests.html', {
        'requests': requests,
        'status_filter': status_filter,
        'leave_summary': leave_summary,
        'today': date.today()
    })

@login_required
def leave_request_create(request):
    """Create a new leave request (for employees)"""
    if not request.user.employee:
        messages.error(request, 'You do not have an employee profile')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, request.FILES)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.employee = request.user.employee
            
            # Calculate business days between start and end date
            business_days = calculate_business_days(
                leave_request.start_date, 
                leave_request.end_date
            )
            leave_request.leave_days = business_days
            
            # Check leave balance if it's annual leave
            if leave_request.leave_type == 'Annual Leave':
                current_year = date.today().year
                try:
                    balance = LeaveBalance.objects.get(
                        employee=request.user.employee,
                        year=current_year,
                        leave_type='Annual Leave'
                    )
                    
                    if balance.remaining_days < business_days:
                        messages.error(request, f'Insufficient annual leave balance. You have {balance.remaining_days} days remaining but requested {business_days} days.')
                        return render(request, 'leave/leave_request_form.html', {'form': form})
                        
                except LeaveBalance.DoesNotExist:
                    # No balance record, let the request go through
                    pass
            
            leave_request.save()
            
            # Notify manager if employee has a department
            if request.user.employee.department:
                # Find department manager
                managers = Employee.objects.filter(
                    department=request.user.employee.department,
                    position__position_name__icontains='Manager'
                )
                
                for manager in managers:
                    if manager.user:
                        create_notification(
                            user=manager.user,
                            notification_type='Leave',
                            title='New Leave Request',
                            message=f'{request.user.employee.full_name} has requested {business_days} days of {leave_request.leave_type}',
                            link=reverse('leave_approval', args=[leave_request.request_id])
                        )
            
            messages.success(request, 'Leave request submitted successfully')
            return redirect('my_leave_requests')
    else:
        form = LeaveRequestForm(initial={
            'start_date': date.today() + timedelta(days=3),
            'end_date': date.today() + timedelta(days=3)
        })
    
    return render(request, 'leave/leave_request_form.html', {'form': form})

@login_required
def leave_request_detail(request, pk):
    """View details of a leave request"""
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    
    # Check if user is authorized to view this request
    if request.user.employee != leave_request.employee and not request.user.role in ['HR', 'Admin']:
        is_manager = request.user.role == 'Manager' and request.user.employee and leave_request.employee.department == request.user.employee.department
        if not is_manager:
            messages.error(request, 'You do not have permission to view this request')
            return redirect('dashboard')
    
    return render(request, 'leave/leave_request_detail.html', {
        'leave_request': leave_request
    })

@login_required
def leave_request_update(request, pk):
    """Update a leave request (only if pending)"""
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    
    # Check if user is the owner and request is pending
    if request.user.employee != leave_request.employee:
        messages.error(request, 'You can only edit your own leave requests')
        return redirect('my_leave_requests')
    
    if leave_request.status != 'Pending':
        messages.error(request, 'You can only edit pending leave requests')
        return redirect('leave_request_detail', pk=pk)
    
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, request.FILES, instance=leave_request)
        if form.is_valid():
            updated_request = form.save(commit=False)
            
            # Recalculate business days
            business_days = calculate_business_days(
                updated_request.start_date, 
                updated_request.end_date
            )
            updated_request.leave_days = business_days
            updated_request.save()
            
            messages.success(request, 'Leave request updated successfully')
            return redirect('my_leave_requests')
    else:
        form = LeaveRequestForm(instance=leave_request)
    
    return render(request, 'leave/leave_request_form.html', {
        'form': form,
        'leave_request': leave_request,
        'is_update': True
    })

@login_required
def leave_request_cancel(request, pk):
    """Cancel a leave request"""
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    
    # Check if user is the owner
    if request.user.employee != leave_request.employee:
        messages.error(request, 'You can only cancel your own leave requests')
        return redirect('my_leave_requests')
    
    # Check if request can be cancelled
    if not leave_request.can_cancel():
        messages.error(request, 'This leave request cannot be cancelled')
        return redirect('leave_request_detail', pk=pk)
    
    if request.method == 'POST':
        leave_request.status = 'Cancelled'
        leave_request.save()
        
        # Update leave balance if it was approved
        if leave_request.status == 'Approved':
            try:
                balance = LeaveBalance.objects.get(
                    employee=leave_request.employee,
                    year=leave_request.start_date.year,
                    leave_type=leave_request.leave_type
                )
                
                balance.used_days -= leave_request.leave_days
                if balance.used_days < 0:
                    balance.used_days = 0
                balance.save()
            except LeaveBalance.DoesNotExist:
                pass
        
        # Notify manager if applicable
        if leave_request.approved_by and leave_request.approved_by.user:
            create_notification(
                user=leave_request.approved_by.user,
                notification_type='Leave',
                title='Leave Request Cancelled',
                message=f'{request.user.employee.full_name} has cancelled their {leave_request.leave_type} request.',
                link=reverse('leave_request_detail', args=[leave_request.request_id])
            )
        
        messages.success(request, 'Leave request cancelled successfully')
        return redirect('my_leave_requests')
    
    return render(request, 'leave/leave_request_cancel.html', {
        'leave_request': leave_request
    })

@login_required
def my_leave_balance(request):
    """View employee's leave balance"""
    if not request.user.employee:
        messages.error(request, 'You do not have an employee profile')
        return redirect('dashboard')
    
    current_year = date.today().year
    
    # Get leave balances for current year
    balances = LeaveBalance.objects.filter(
        employee=request.user.employee,
        year=current_year
    ).order_by('leave_type')
    
    # If no balance records exist, check if HR has policy for default values
    if not balances.exists():
        # This would integrate with company policy settings
        # For now, we'll just show a message
        messages.info(request, 'No leave balance records found for the current year.')
    
    # Get leave history for current year
    leave_history = LeaveRequest.objects.filter(
        employee=request.user.employee,
        start_date__year=current_year,
        status='Approved'
    ).order_by('-start_date')
    
    return render(request, 'leave/my_leave_balance.html', {
        'balances': balances,
        'leave_history': leave_history,
        'current_year': current_year
    })

# Manager Views
@login_required
@manager_required
def pending_leave_requests(request):
    """View pending leave requests for manager's department"""
    if not request.user.employee or not request.user.employee.department:
        messages.error(request, 'You are not assigned to any department')
        return redirect('dashboard')
    
    department = request.user.employee.department
    
    # Get pending requests for this department
    pending_requests = LeaveRequest.objects.filter(
        employee__department=department,
        status='Pending'
    ).order_by('start_date')
    
    # Get recently approved/rejected requests
    recent_processed = LeaveRequest.objects.filter(
        employee__department=department,
        status__in=['Approved', 'Rejected'],
        approval_date__gte=date.today() - timedelta(days=30)
    ).order_by('-approval_date')[:10]
    
    return render(request, 'leave/pending_leave_requests.html', {
        'pending_requests': pending_requests,
        'recent_processed': recent_processed,
        'department': department
    })

@login_required
@manager_required
def leave_approval(request, pk):
    """Approve/reject leave requests (for managers and HR)"""
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    
    # Check if user is authorized to approve this request
    is_hr_or_admin = request.user.role in ['HR', 'Admin']
    is_department_manager = (request.user.role == 'Manager' and request.user.employee and 
                           request.user.employee.department == leave_request.employee.department)
    
    if not (is_hr_or_admin or is_department_manager):
        messages.error(request, 'You do not have permission to approve this request')
        return redirect('dashboard')
    
    if leave_request.status != 'Pending':
        messages.error(request, 'This request is not pending approval')
        return redirect('all_leave_requests' if is_hr_or_admin else 'pending_leave_requests')
    
    if request.method == 'POST':
        form = LeaveApprovalForm(request.POST, instance=leave_request)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.approved_by = request.user.employee
            leave_request.approval_date = date.today()
            leave_request.save()
            
            # Update leave balance if approved
            if leave_request.status == 'Approved':
                # Get or create leave balance
                balance, created = LeaveBalance.objects.get_or_create(
                    employee=leave_request.employee,
                    year=leave_request.start_date.year,
                    leave_type=leave_request.leave_type,
                    defaults={
                        'total_days': 0 if leave_request.leave_type != 'Annual Leave' else 15,  # Default annual leave days
                        'used_days': 0,
                        'carry_over': 0
                    }
                )
                
                # Update used days
                balance.used_days += leave_request.leave_days
                balance.save()
            
            # Send notification to employee
            if leave_request.employee.user:
                create_notification(
                    user=leave_request.employee.user,
                    notification_type='Leave',
                    title=f'Leave Request {leave_request.status}',
                    message=f'Your {leave_request.leave_type} request has been {leave_request.status.lower()}.',
                    link=reverse('leave_request_detail', args=[leave_request.request_id])
                )
            
            # Send email notification
            send_leave_status_email(leave_request)
            
            messages.success(request, f'Leave request {leave_request.status.lower()}')
            return redirect('all_leave_requests' if is_hr_or_admin else 'pending_leave_requests')
    else:
        form = LeaveApprovalForm(instance=leave_request)
    
    # Get employee's leave history
    leave_history = LeaveRequest.objects.filter(
        employee=leave_request.employee,
        status='Approved'
    ).order_by('-start_date')[:5]
    
    # Get employee's current leave balance
    try:
        leave_balance = LeaveBalance.objects.get(
            employee=leave_request.employee,
            year=leave_request.start_date.year,
            leave_type=leave_request.leave_type
        )
    except LeaveBalance.DoesNotExist:
        leave_balance = None
    
    return render(request, 'leave/leave_approval_form.html', {
        'form': form,
        'leave_request': leave_request,
        'leave_history': leave_history,
        'leave_balance': leave_balance
    })

# HR Views
@login_required
@hr_required
def all_leave_requests(request):
    """View all leave requests (for HR)"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    department_filter = request.GET.get('department', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    query = request.GET.get('q', '')  # For searching by employee name
    
    # Start with all requests
    requests = LeaveRequest.objects.all()
    
    # Apply filters
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    if department_filter:
        requests = requests.filter(employee__department_id=department_filter)
    
    if date_from:
        requests = requests.filter(start_date__gte=date_from)
    
    if date_to:
        requests = requests.filter(end_date__lte=date_to)
    
    if query:
        requests = requests.filter(employee__full_name__icontains=query)
    
    # Order by creation date (newest first)
    requests = requests.order_by('-created_date')
    
    # Paginate results
    paginator = Paginator(requests, 10)  # 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get departments for filter dropdown
    departments = Department.objects.all()
    
    # Date range form
    date_range_form = DateRangeForm(initial={
        'start_date': date_from or (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'),
        'end_date': date_to or date.today().strftime('%Y-%m-%d')
    })
    
    return render(request, 'leave/all_leave_requests.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'department_filter': department_filter,
        'query': query,
        'departments': departments,
        'date_range_form': date_range_form
    })

@login_required
@hr_required
def leave_report(request):
    """Generate leave reports"""
    # Get date range parameters
    year = int(request.GET.get('year', date.today().year))
    month = int(request.GET.get('month', 0))  # 0 means all months
    
    # Get all approved leaves for the given period
    leaves = LeaveRequest.objects.filter(status='Approved')
    
    if month > 0:
        leaves = leaves.filter(start_date__year=year, start_date__month=month)
    else:
        leaves = leaves.filter(start_date__year=year)
    
    # Calculate leave statistics by department
    departments = Department.objects.all()
    department_stats = []
    
    for dept in departments:
        dept_leaves = leaves.filter(employee__department=dept)
        
        # Count by leave type
        annual_leaves = dept_leaves.filter(leave_type='Annual Leave').aggregate(
            count=Count('request_id'),
            days=Sum('leave_days')
        )
        
        sick_leaves = dept_leaves.filter(leave_type='Sick Leave').aggregate(
            count=Count('request_id'),
            days=Sum('leave_days')
        )
        
        other_leaves = dept_leaves.exclude(
            leave_type__in=['Annual Leave', 'Sick Leave']
        ).aggregate(
            count=Count('request_id'),
            days=Sum('leave_days')
        )
        
        # Add to department stats
        department_stats.append({
            'department': dept,
            'annual_count': annual_leaves['count'] or 0,
            'annual_days': annual_leaves['days'] or 0,
            'sick_count': sick_leaves['count'] or 0,
            'sick_days': sick_leaves['days'] or 0,
            'other_count': other_leaves['count'] or 0,
            'other_days': other_leaves['days'] or 0,
            'total_count': (annual_leaves['count'] or 0) + (sick_leaves['count'] or 0) + (other_leaves['count'] or 0),
            'total_days': (annual_leaves['days'] or 0) + (sick_leaves['days'] or 0) + (other_leaves['days'] or 0)
        })
    
    # Calculate leave statistics by month (if showing full year)
    month_stats = []
    if month == 0:
        for m in range(1, 13):
            month_leaves = leaves.filter(start_date__month=m)
            
            month_stats.append({
                'month': calendar.month_name[m],
                'count': month_leaves.count(),
                'days': month_leaves.aggregate(days=Sum('leave_days'))['days'] or 0
            })
    
    # Get all years with leave data for filter
    years_with_leaves = LeaveRequest.objects.filter(status='Approved').dates('start_date', 'year')
    available_years = sorted(set([d.year for d in years_with_leaves]), reverse=True)
    
    # If no years found, add current year
    if not available_years:
        available_years = [date.today().year]
    
    return render(request, 'leave/leave_report.html', {
        'department_stats': department_stats,
        'month_stats': month_stats,
        'year': year,
        'month': month,
        'available_years': available_years,
        'months': [(i, calendar.month_name[i]) for i in range(1, 13)]
    })

@login_required
@hr_required
def department_leave_report(request, department_id):
    """Detailed leave report for a specific department"""
    department = get_object_or_404(Department, pk=department_id)
    
    # Get date range parameters
    year = int(request.GET.get('year', date.today().year))
    
    # Get all approved leaves for the department in the given year
    leaves = LeaveRequest.objects.filter(
        employee__department=department,
        status='Approved',
        start_date__year=year
    ).order_by('start_date')
    
    # Calculate leave statistics by employee
    employees = Employee.objects.filter(department=department, status='Working')
    employee_stats = []
    
    for emp in employees:
        emp_leaves = leaves.filter(employee=emp)
        
        annual_days = emp_leaves.filter(leave_type='Annual Leave').aggregate(days=Sum('leave_days'))['days'] or 0
        sick_days = emp_leaves.filter(leave_type='Sick Leave').aggregate(days=Sum('leave_days'))['days'] or 0
        other_days = emp_leaves.exclude(leave_type__in=['Annual Leave', 'Sick Leave']).aggregate(days=Sum('leave_days'))['days'] or 0
        
        employee_stats.append({
            'employee': emp,
            'annual_days': annual_days,
            'sick_days': sick_days,
            'other_days': other_days,
            'total_days': annual_days + sick_days + other_days
        })
    
    # Sort by total leave days (descending)
    employee_stats.sort(key=lambda x: x['total_days'], reverse=True)
    
    # Get all years with leave data for filter
    years_with_leaves = LeaveRequest.objects.filter(
        employee__department=department,
        status='Approved'
    ).dates('start_date', 'year')
    
    available_years = sorted(set([d.year for d in years_with_leaves]), reverse=True)
    
    # If no years found, add current year
    if not available_years:
        available_years = [date.today().year]
    
    return render(request, 'leave/department_leave_report.html', {
        'department': department,
        'employee_stats': employee_stats,
        'leaves': leaves,
        'year': year,
        'available_years': available_years
    })

@login_required
@hr_required
def employee_leave_report(request, employee_id):
    """Detailed leave report for a specific employee"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    # Get date range parameters
    year = int(request.GET.get('year', date.today().year))
    
    # Get all leaves for the employee
    leaves = LeaveRequest.objects.filter(
        employee=employee,
        start_date__year=year
    ).order_by('-start_date')
    
    # Get leave balances
    balances = LeaveBalance.objects.filter(
        employee=employee,
        year=year
    ).order_by('leave_type')
    
    # Calculate leave statistics by month
    month_stats = []
    for m in range(1, 13):
        month_leaves = leaves.filter(
            start_date__month=m,
            status='Approved'
        )
        
        if month_leaves.exists():
            month_stats.append({
                'month': calendar.month_name[m],
                'count': month_leaves.count(),
                'days': month_leaves.aggregate(days=Sum('leave_days'))['days'] or 0
            })
    
    # Calculate leave statistics by type
    leave_type_stats = []
    for leave_type, _ in LeaveRequest.LEAVE_TYPE_CHOICES:
        type_leaves = leaves.filter(
            leave_type=leave_type,
            status='Approved'
        )
        
        if type_leaves.exists():
            leave_type_stats.append({
                'type': leave_type,
                'count': type_leaves.count(),
                'days': type_leaves.aggregate(days=Sum('leave_days'))['days'] or 0
            })
    
    # Get all years with leave data for filter
    years_with_leaves = LeaveRequest.objects.filter(employee=employee).dates('start_date', 'year')
    available_years = sorted(set([d.year for d in years_with_leaves]), reverse=True)
    
    # If no years found, add current year
    if not available_years:
        available_years = [date.today().year]
    
    return render(request, 'leave/employee_leave_report.html', {
        'employee': employee,
        'leaves': leaves,
        'balances': balances,
        'month_stats': month_stats,
        'leave_type_stats': leave_type_stats,
        'year': year,
        'available_years': available_years
    })

@login_required
@hr_required
def employee_leave_balance(request, employee_id):
    """View and edit employee leave balance"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    # Get the year parameter, default to current year
    year = int(request.GET.get('year', date.today().year))
    
    # Get or create leave balances for all leave types
    balances = []
    for leave_type, leave_name in LeaveRequest.LEAVE_TYPE_CHOICES:
        balance, created = LeaveBalance.objects.get_or_create(
            employee=employee,
            year=year,
            leave_type=leave_type,
            defaults={
                'total_days': 15 if leave_type == 'Annual Leave' else 0,
                'used_days': 0,
                'carry_over': 0
            }
        )
        balances.append(balance)
    
    # Handle form submission
    if request.method == 'POST':
        balance_id = request.POST.get('balance_id')
        balance = get_object_or_404(LeaveBalance, balance_id=balance_id, employee=employee)
        
        form = LeaveBalanceForm(request.POST, instance=balance)
        if form.is_valid():
            form.save()
            messages.success(request, f'{balance.leave_type} balance updated successfully')
            return redirect('employee_leave_balance', employee_id=employee_id)
    
    # Get leave history for the year
    leave_history = LeaveRequest.objects.filter(
        employee=employee,
        start_date__year=year,
        status='Approved'
    ).order_by('-start_date')
    
    # Get all years with balance data for filter
    years_with_balances = LeaveBalance.objects.filter(employee=employee).values_list('year', flat=True).distinct()
    available_years = sorted(set(years_with_balances), reverse=True)
    
    # If no years found, add current year
    if not available_years:
        available_years = [date.today().year]
    
    return render(request, 'leave/employee_leave_balance.html', {
        'employee': employee,
        'balances': balances,
        'leave_history': leave_history,
        'year': year,
        'available_years': available_years
    })

@login_required
@hr_required
def export_leave_requests(request):
    """Export leave requests as CSV"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    department_filter = request.GET.get('department', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Start with all requests
    requests = LeaveRequest.objects.all()
    
    # Apply filters
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    if department_filter:
        requests = requests.filter(employee__department_id=department_filter)
    
    if date_from:
        requests = requests.filter(start_date__gte=date_from)
    
    if date_to:
        requests = requests.filter(end_date__lte=date_to)
    
    # Order by creation date (newest first)
    requests = requests.order_by('-created_date')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="leave_requests.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Request ID', 'Employee', 'Department', 'Leave Type', 
        'Start Date', 'End Date', 'Leave Days', 'Status',
        'Approved By', 'Approval Date', 'Reason', 'Created Date'
    ])
    
    for req in requests:
        writer.writerow([
            req.request_id,
            req.employee.full_name,
            req.employee.department.department_name if req.employee.department else 'N/A',
            req.leave_type,
            req.start_date,
            req.end_date,
            req.leave_days,
            req.status,
            req.approved_by.full_name if req.approved_by else 'N/A',
            req.approval_date or 'N/A',
            req.reason or 'N/A',
            req.created_date.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response

# Helper Functions
def calculate_business_days(start_date, end_date):
    """Calculate number of business days between two dates"""
    days = 0
    current_date = start_date
    while current_date <= end_date:
        # Monday = 0, Sunday = 6
        if current_date.weekday() < 5:  
            days += 1
        current_date += timedelta(days=1)
    return days

def send_leave_status_email(leave_request):
    """Send email to employee about leave request status change"""
    subject = f'Leave Request {leave_request.status}'
    message = f'Your leave request from {leave_request.start_date} to {leave_request.end_date} has been {leave_request.status.lower()}.'
    if leave_request.approval_notes:
        message += f'\n\nNotes: {leave_request.approval_notes}'
    
    employee_email = leave_request.employee.email
    if employee_email:
        from django.core.mail import send_mail
        send_mail(
            subject, 
            message,
            None,  # Use DEFAULT_FROM_EMAIL from settings
            [employee_email]
        )
