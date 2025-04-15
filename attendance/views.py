from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum, Avg
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import date, datetime, timedelta
import calendar
import csv
import json

from .models import Attendance, WorkShift, ShiftAssignment
from .forms import AttendanceForm, WorkShiftForm, ShiftAssignmentForm, AttendanceImportForm
from employee.models import Employee, Department
from accounts.decorators import *

# Employee-facing views
@login_required
@employee_approved_required
def my_attendance(request):
    """View personal attendance records"""
    if not request.user.employee:
        messages.error(request, 'You do not have an employee profile')
        return redirect('dashboard')
    
    # Get date filters from request
    month = request.GET.get('month', timezone.now().month)
    year = request.GET.get('year', timezone.now().year)
    
    try:
        month = int(month)
        year = int(year)
    except ValueError:
        month = timezone.now().month
        year = timezone.now().year
    
    # Create date range for the specified month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # Get attendance records for the date range
    attendance_records = Attendance.objects.filter(
        employee=request.user.employee,
        work_date__gte=start_date,
        work_date__lte=end_date
    ).order_by('work_date')
    
    # Calculate summary statistics
    total_days = (end_date - start_date).days + 1
    weekdays = sum(1 for i in range(total_days) if (start_date + timedelta(days=i)).weekday() < 5)
    
    present_days = attendance_records.filter(status='Present').count()
    absent_days = attendance_records.filter(status='Absent').count()
    leave_days = attendance_records.filter(status='On Leave').count()
    holiday_days = attendance_records.filter(status='Holiday').count()
    business_trip_days = attendance_records.filter(status='Business Trip').count()
    
    total_work_hours = attendance_records.aggregate(
        total_hours=Sum('actual_work_hours')
    )['total_hours'] or 0
    
    total_overtime = attendance_records.aggregate(
        total_ot=Sum('overtime_hours')
    )['total_ot'] or 0
    
    # Get today's attendance record
    today = date.today()
    try:
        today_attendance = attendance_records.get(work_date=today)
        can_check_in = today_attendance.time_in is None
        can_check_out = today_attendance.time_in is not None and today_attendance.time_out is None
    except Attendance.DoesNotExist:
        today_attendance = None
        can_check_in = True
        can_check_out = False
    
    # Get all available months for filter
    available_months = Attendance.objects.filter(
        employee=request.user.employee
    ).dates('work_date', 'month')
    
    # Create month choices for the dropdown
    month_choices = []
    for m in available_months:
        month_choices.append({
            'month': m.month,
            'year': m.year,
            'name': m.strftime('%B %Y')
        })
    
    # If no records exist yet, add current month
    if not month_choices:
        current_month = timezone.now()
        month_choices.append({
            'month': current_month.month,
            'year': current_month.year,
            'name': current_month.strftime('%B %Y')
        })
    
    context = {
        'attendance_records': attendance_records,
        'today_attendance': today_attendance,
        'can_check_in': can_check_in,
        'can_check_out': can_check_out,
        'today': today,
        'month': month,
        'year': year,
        'month_name': calendar.month_name[month],
        'month_choices': month_choices,
        'summary': {
            'total_days': total_days,
            'weekdays': weekdays,
            'present_days': present_days,
            'absent_days': absent_days,
            'leave_days': leave_days,
            'holiday_days': holiday_days,
            'business_trip_days': business_trip_days,
            'total_work_hours': total_work_hours,
            'total_overtime': total_overtime
        }
    }
    
    return render(request, 'attendance/my_attendance.html', context)

@login_required
@employee_required
def attendance_check_in(request):
    if not request.user.employee:
        messages.error(request, 'You do not have an employee profile')
        return redirect('dashboard')
    
    today = date.today()
    now = datetime.now().time()
    
    try:
        # Check if there's already a record for today
        attendance = Attendance.objects.get(employee=request.user.employee, work_date=today)
        
        if attendance.time_in:
            messages.info(request, 'You have already checked in today')
        else:
            attendance.time_in = now
            attendance.status = 'Present'
            attendance.save()
            messages.success(request, 'Check-in successful')
    
    except Attendance.DoesNotExist:
        # Create a new attendance record
        attendance = Attendance(
            employee=request.user.employee,
            work_date=today,
            time_in=now,
            status='Present'
        )
        
        # Check if employee has an assigned shift for today
        current_shift = ShiftAssignment.objects.filter(
            employee=request.user.employee,
            effective_date__lte=today,
            status='Active'
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).first()
        
        if current_shift:
            attendance.shift = current_shift.shift
        
        attendance.save()
        messages.success(request, 'Check-in successful')
    
    return redirect('my_attendance')

@login_required
@employee_required
def attendance_check_out(request):
    if not request.user.employee:
        messages.error(request, 'You do not have an employee profile')
        return redirect('dashboard')
    
    today = date.today()
    now = datetime.now().time()
    
    try:
        # Get today's attendance record
        attendance = Attendance.objects.get(employee=request.user.employee, work_date=today)
        
        if not attendance.time_in:
            messages.error(request, 'You need to check in first')
        elif attendance.time_out:
            messages.info(request, 'You have already checked out today')
        else:
            attendance.time_out = now
            
            # Calculate actual work hours
            time_in_delta = datetime.combine(today, attendance.time_in)
            time_out_delta = datetime.combine(today, now)
            
            if time_out_delta < time_in_delta:  # If time_out is on the next day
                time_out_delta = datetime.combine(today + timedelta(days=1), now)
            
            diff_seconds = (time_out_delta - time_in_delta).total_seconds()
            diff_hours = diff_seconds / 3600
            
            attendance.actual_work_hours = round(diff_hours, 2)
            
            # Calculate overtime if a shift is assigned
            if attendance.shift:
                # Get shift end time
                shift_end = attendance.shift.end_time
                
                # Handle overnight shifts
                shift_end_delta = datetime.combine(today, shift_end)
                if shift_end < attendance.shift.start_time:  # Overnight shift
                    shift_end_delta = datetime.combine(today + timedelta(days=1), shift_end)
                
                # Calculate standard shift hours
                shift_start_delta = datetime.combine(today, attendance.shift.start_time)
                shift_hours = (shift_end_delta - shift_start_delta).total_seconds() / 3600
                
                # If worked more than shift hours, calculate overtime
                if diff_hours > shift_hours:
                    attendance.overtime_hours = round(diff_hours - shift_hours, 2)
            
            attendance.save()
            messages.success(request, 'Check-out successful')
    
    except Attendance.DoesNotExist:
        messages.error(request, 'You need to check in first')
    
    return redirect('my_attendance')

# Calendar view for attendance
@login_required
def attendance_calendar(request):
    """Calendar view for attendance"""
    return render(request, 'attendance/calendar.html')

@login_required
def calendar_data(request):
    """API endpoint to get attendance calendar data"""
    # Get date range from request
    start_date = request.GET.get('start', '')
    end_date = request.GET.get('end', '')
    view_type = request.GET.get('view', 'personal')  # personal, department, company
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        # Default to current month if dates are invalid
        today = date.today()
        start_date = date(today.year, today.month, 1)
        _, last_day = calendar.monthrange(today.year, today.month)
        end_date = date(today.year, today.month, last_day)
    
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
                color = '#6f42c1'  # purple for business trip
            
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
    
    # Handle department view (manager and above)
    elif view_type == 'department' and request.user.role in ['Manager', 'HR', 'Admin']:
        if not request.user.employee or not request.user.employee.department:
            return JsonResponse({'events': []})
        
        department = request.user.employee.department
        
        # Get all employees in department
        employees = Employee.objects.filter(department=department, status='Working')
        
        # We'll create a summary of daily attendance
        date_range = (end_date - start_date).days + 1
        for day_offset in range(date_range):
            day = start_date + timedelta(days=day_offset)
            
            # Count attendance by status for this day
            attendance_by_status = Attendance.objects.filter(
                employee__in=employees,
                work_date=day
            ).values('status').annotate(count=Count('status'))
            
            status_counts = {status: 0 for status in ['Present', 'Absent', 'On Leave', 'Holiday', 'Business Trip']}
            for item in attendance_by_status:
                status_counts[item['status']] = item['count']
            
            # Create a summary event
            title = (f"Present: {status_counts['Present']}, "
                     f"Absent: {status_counts['Absent']}, "
                     f"Leave: {status_counts['On Leave']}")
            
            events.append({
                'id': f'dept-summary-{day.strftime("%Y-%m-%d")}',
                'title': title,
                'start': day.strftime('%Y-%m-%d'),
                'color': '#3788d8',  # blue for department summary
                'type': 'department_summary',
                'present': status_counts['Present'],
                'absent': status_counts['Absent'],
                'leave': status_counts['On Leave'],
                'holiday': status_counts['Holiday'],
                'business_trip': status_counts['Business Trip'],
                'allDay': True
            })
    
    # Company-wide view (HR and Admin only)
    elif view_type == 'company' and request.user.role in ['HR', 'Admin']:
        date_range = (end_date - start_date).days + 1
        for day_offset in range(date_range):
            day = start_date + timedelta(days=day_offset)
            
            # Count attendance by status for this day across all employees
            attendance_by_status = Attendance.objects.filter(
                work_date=day
            ).values('status').annotate(count=Count('status'))
            
            status_counts = {status: 0 for status in ['Present', 'Absent', 'On Leave', 'Holiday', 'Business Trip']}
            for item in attendance_by_status:
                status_counts[item['status']] = item['count']
            
            # Create a summary event
            title = (f"Present: {status_counts['Present']}, "
                     f"Absent: {status_counts['Absent']}, "
                     f"Leave: {status_counts['On Leave']}")
            
            events.append({
                'id': f'company-summary-{day.strftime("%Y-%m-%d")}',
                'title': title,
                'start': day.strftime('%Y-%m-%d'),
                'color': '#3788d8',  # blue for company summary
                'type': 'company_summary',
                'present': status_counts['Present'],
                'absent': status_counts['Absent'],
                'leave': status_counts['On Leave'],
                'holiday': status_counts['Holiday'],
                'business_trip': status_counts['Business Trip'],
                'allDay': True
            })
    
    return JsonResponse({'events': events})

# Work shift management
@login_required
@hr_required
def shift_list(request):
    """List all work shifts"""
    shifts = WorkShift.objects.all().order_by('-status', 'shift_name')
    
    return render(request, 'attendance/shift_list.html', {'shifts': shifts})

@login_required
@hr_required
def shift_create(request):
    """Create a new work shift"""
    if request.method == 'POST':
        form = WorkShiftForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Work shift created successfully')
            return redirect('shift_list')
    else:
        form = WorkShiftForm()
    
    return render(request, 'attendance/shift_form.html', {
        'form': form,
        'title': 'Create Work Shift'
    })

@login_required
@hr_required
def shift_update(request, pk):
    """Update a work shift"""
    shift = get_object_or_404(WorkShift, pk=pk)
    
    if request.method == 'POST':
        form = WorkShiftForm(request.POST, instance=shift)
        if form.is_valid():
            form.save()
            messages.success(request, 'Work shift updated successfully')
            return redirect('shift_list')
    else:
        form = WorkShiftForm(instance=shift)
    
    return render(request, 'attendance/shift_form.html', {
        'form': form,
        'title': 'Update Work Shift',
        'shift': shift
    })

@login_required
@hr_required
def shift_delete(request, pk):
    """Delete a work shift"""
    shift = get_object_or_404(WorkShift, pk=pk)
    
    if request.method == 'POST':
        # Check if shift is assigned to any employees
        if ShiftAssignment.objects.filter(shift=shift, status='Active').exists():
            messages.error(request, 'Cannot delete shift. It is currently assigned to employees.')
        else:
            shift.delete()
            messages.success(request, 'Work shift deleted successfully')
        return redirect('shift_list')
    
    return render(request, 'attendance/confirm_delete.html', {
        'object': shift,
        'title': 'Delete Work Shift',
        'message': 'Are you sure you want to delete this work shift?'
    })

# Shift assignment management
@login_required
@hr_required
def shift_assignment_list(request):
    """List all shift assignments"""
    # Get filter parameters
    employee_filter = request.GET.get('employee', '')
    shift_filter = request.GET.get('shift', '')
    status_filter = request.GET.get('status', '')
    
    # Build query
    assignments = ShiftAssignment.objects.all()
    
    if employee_filter:
        assignments = assignments.filter(employee_id=employee_filter)
    
    if shift_filter:
        assignments = assignments.filter(shift_id=shift_filter)
    
    if status_filter:
        assignments = assignments.filter(status=status_filter)
    
    # Order by most recent first
    assignments = assignments.order_by('-assignment_date')
    
    # Get filter options
    employees = Employee.objects.filter(status='Working').order_by('full_name')
    shifts = WorkShift.objects.filter(status=1).order_by('shift_name')
    
    return render(request, 'attendance/shift_assignment_list.html', {
        'assignments': assignments,
        'employees': employees,
        'shifts': shifts,
        'employee_filter': employee_filter,
        'shift_filter': shift_filter,
        'status_filter': status_filter
    })

@login_required
@hr_required
def shift_assignment_create(request):
    """Create a new shift assignment"""
    if request.method == 'POST':
        form = ShiftAssignmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Shift assignment created successfully')
            return redirect('shift_assignment_list')
    else:
        # Pre-fill date fields with today's date
        initial_data = {
            'assignment_date': date.today(),
            'effective_date': date.today()
        }
        
        # If employee_id is in query params, pre-select that employee
        employee_id = request.GET.get('employee_id')
        if employee_id:
            try:
                employee = Employee.objects.get(pk=employee_id)
                initial_data['employee'] = employee
            except Employee.DoesNotExist:
                pass
        
        form = ShiftAssignmentForm(initial=initial_data)
    
    return render(request, 'attendance/shift_assignment_form.html', {
        'form': form,
        'title': 'Create Shift Assignment'
    })

@login_required
@hr_required
def shift_assignment_update(request, pk):
    """Update a shift assignment"""
    assignment = get_object_or_404(ShiftAssignment, pk=pk)
    
    if request.method == 'POST':
        form = ShiftAssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Shift assignment updated successfully')
            return redirect('shift_assignment_list')
    else:
        form = ShiftAssignmentForm(instance=assignment)
    
    return render(request, 'attendance/shift_assignment_form.html', {
        'form': form,
        'title': 'Update Shift Assignment',
        'assignment': assignment
    })

@login_required
@hr_required
def shift_assignment_delete(request, pk):
    """Delete a shift assignment"""
    assignment = get_object_or_404(ShiftAssignment, pk=pk)
    
    if request.method == 'POST':
        assignment.delete()
        messages.success(request, 'Shift assignment deleted successfully')
        return redirect('shift_assignment_list')
    
    return render(request, 'attendance/confirm_delete.html', {
        'object': assignment,
        'title': 'Delete Shift Assignment',
        'message': f'Are you sure you want to delete the shift assignment for {assignment.employee.full_name}?'
    })

# Admin attendance management
@login_required
@hr_required
def attendance_report(request):
    """Generate attendance report with filtering options"""
    # Get filter parameters
    department_id = request.GET.get('department', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status = request.GET.get('status', '')
    
    # Default to current month if no dates specified
    if not date_from or not date_to:
        today = date.today()
        first_day = today.replace(day=1)
        last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        date_from = first_day.strftime('%Y-%m-%d')
        date_to = last_day.strftime('%Y-%m-%d')
    
    # Build query for attendance
    query = Q()
    
    if date_from:
        query &= Q(work_date__gte=date_from)
    
    if date_to:
        query &= Q(work_date__lte=date_to)
    
    if status:
        query &= Q(status=status)
    
    if department_id:
        query &= Q(employee__department_id=department_id)
    
    # Get attendance records
    attendance_records = Attendance.objects.filter(query).select_related(
        'employee', 'employee__department', 'shift'
    ).order_by('-work_date')
    
    # Calculate summary statistics
    summary = {
        'total_records': attendance_records.count(),
        'present': attendance_records.filter(status='Present').count(),
        'absent': attendance_records.filter(status='Absent').count(),
        'on_leave': attendance_records.filter(status='On Leave').count(),
        'holiday': attendance_records.filter(status='Holiday').count(),
        'business_trip': attendance_records.filter(status='Business Trip').count(),
        'total_hours': attendance_records.aggregate(total=Sum('actual_work_hours'))['total'] or 0,
        'total_overtime': attendance_records.aggregate(total=Sum('overtime_hours'))['total'] or 0
    }
    
    # Get departments for filter
    departments = Department.objects.filter(status=1).order_by('department_name')
    
    # Handle export request
    if 'export' in request.GET:
        return export_attendance(request, attendance_records)
    
    # Paginate results
    paginator = Paginator(attendance_records, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'departments': departments,
        'department_id': department_id,
        'date_from': date_from,
        'date_to': date_to,
        'status': status,
        'summary': summary,
        'status_choices': Attendance.STATUS_CHOICES
    }
    
    return render(request, 'attendance/report.html', context)

@login_required
@hr_required
def department_attendance(request, department_id):
    """View attendance for a specific department"""
    department = get_object_or_404(Department, pk=department_id)
    
    # Get date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Default to current month if no dates specified
    if not date_from or not date_to:
        today = date.today()
        first_day = today.replace(day=1)
        last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        date_from = first_day.strftime('%Y-%m-%d')
        date_to = last_day.strftime('%Y-%m-%d')
    
    # Get employees in this department
    employees = Employee.objects.filter(department=department, status='Working').order_by('full_name')
    
    # Get attendance summary for each employee
    employee_attendance = []
    
    for employee in employees:
        attendance = Attendance.objects.filter(
            employee=employee,
            work_date__gte=date_from,
            work_date__lte=date_to
        )
        
        # Calculate summary
        summary = {
            'employee': employee,
            'total_records': attendance.count(),
            'present': attendance.filter(status='Present').count(),
            'absent': attendance.filter(status='Absent').count(),
            'on_leave': attendance.filter(status='On Leave').count(),
            'holiday': attendance.filter(status='Holiday').count(),
            'business_trip': attendance.filter(status='Business Trip').count(),
            'total_hours': attendance.aggregate(total=Sum('actual_work_hours'))['total'] or 0,
            'total_overtime': attendance.aggregate(total=Sum('overtime_hours'))['total'] or 0,
            'avg_hours': attendance.filter(status='Present').aggregate(
                avg=Avg('actual_work_hours')
            )['avg'] or 0
        }
        
        employee_attendance.append(summary)
    
    # Department summary
    department_summary = {
        'total_employees': len(employees),
        'present': Attendance.objects.filter(
            employee__department=department,
            work_date__gte=date_from,
            work_date__lte=date_to,
            status='Present'
        ).count(),
        'absent': Attendance.objects.filter(
            employee__department=department,
            work_date__gte=date_from,
            work_date__lte=date_to,
            status='Absent'
        ).count(),
        'on_leave': Attendance.objects.filter(
            employee__department=department,
            work_date__gte=date_from,
            work_date__lte=date_to,
            status='On Leave'
        ).count()
    }
    
    context = {
        'department': department,
        'employee_attendance': employee_attendance,
        'department_summary': department_summary,
        'date_from': date_from,
        'date_to': date_to
    }
    
    return render(request, 'attendance/department_attendance.html', context)

@login_required
@hr_required
def employee_attendance(request, employee_id):
    """View detailed attendance for a specific employee"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    # Get date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Default to current month if no dates specified
    if not date_from or not date_to:
        today = date.today()
        first_day = today.replace(day=1)
        last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        date_from = first_day.strftime('%Y-%m-%d')
        date_to = last_day.strftime('%Y-%m-%d')
    
    # Get attendance records
    attendance_records = Attendance.objects.filter(
        employee=employee,
        work_date__gte=date_from,
        work_date__lte=date_to
    ).select_related('shift').order_by('-work_date')
    
    # Calculate summary statistics
    summary = {
        'total_records': attendance_records.count(),
        'present': attendance_records.filter(status='Present').count(),
        'absent': attendance_records.filter(status='Absent').count(),
        'on_leave': attendance_records.filter(status='On Leave').count(),
        'holiday': attendance_records.filter(status='Holiday').count(),
        'business_trip': attendance_records.filter(status='Business Trip').count(),
        'total_hours': attendance_records.aggregate(total=Sum('actual_work_hours'))['total'] or 0,
        'total_overtime': attendance_records.aggregate(total=Sum('overtime_hours'))['total'] or 0
    }
    
    # Get current shift assignment
    current_shift = ShiftAssignment.objects.filter(
        employee=employee,
        status='Active',
        effective_date__lte=date.today()
    ).filter(
        Q(end_date__gte=date.today()) | Q(end_date__isnull=True)
    ).first()
    
    context = {
        'employee': employee,
        'attendance_records': attendance_records,
        'summary': summary,
        'date_from': date_from,
        'date_to': date_to,
        'current_shift': current_shift
    }
    
    return render(request, 'attendance/employee_attendance.html', context)

@login_required
@hr_required
def attendance_record_create(request):
    """Create a new attendance record (manual entry)"""
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            attendance = form.save()
            messages.success(request, 'Attendance record created successfully')
            
            # Redirect to employee's attendance page if accessed from there
            employee_id = request.POST.get('employee_id')
            if employee_id:
                return redirect('employee_attendance', employee_id=employee_id)
            return redirect('attendance_report')
    else:
        # Pre-fill with today's date and employee from query params if provided
        initial_data = {'work_date': date.today()}
        
        employee_id = request.GET.get('employee_id')
        if employee_id:
            try:
                employee = Employee.objects.get(pk=employee_id)
                initial_data['employee'] = employee
                
                # Check if record already exists for this employee/date
                existing = Attendance.objects.filter(
                    employee=employee,
                    work_date=date.today()
                ).first()
                
                if existing:
                    messages.warning(request, f'Attendance record already exists for {employee.full_name} today')
                    return redirect('attendance_record_update', pk=existing.attendance_id)
                
                # Pre-select shift if employee has an active assignment
                current_shift = ShiftAssignment.objects.filter(
                    employee=employee,
                    status='Active',
                    effective_date__lte=date.today()
                ).filter(
                    Q(end_date__gte=date.today()) | Q(end_date__isnull=True)
                ).first()
                
                if current_shift:
                    initial_data['shift'] = current_shift.shift
                
            except Employee.DoesNotExist:
                pass
        
        form = AttendanceForm(initial=initial_data)
    
    return render(request, 'attendance/attendance_form.html', {
        'form': form,
        'title': 'Create Attendance Record'
    })

@login_required
@hr_required
def attendance_record_update(request, pk):
    """Update an attendance record"""
    attendance = get_object_or_404(Attendance, pk=pk)
    
    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=attendance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance record updated successfully')
            
            # Redirect based on referer
            referer = request.META.get('HTTP_REFERER', '')
            if 'employee_attendance' in referer:
                return redirect('employee_attendance', employee_id=attendance.employee.employee_id)
            return redirect('attendance_report')
    else:
        form = AttendanceForm(instance=attendance)
    
    return render(request, 'attendance/attendance_form.html', {
        'form': form,
        'title': 'Update Attendance Record',
        'attendance': attendance
    })

@login_required
@hr_required
def attendance_record_delete(request, pk):
    """Delete an attendance record"""
    attendance = get_object_or_404(Attendance, pk=pk)
    
    if request.method == 'POST':
        employee_id = attendance.employee.employee_id
        attendance.delete()
        messages.success(request, 'Attendance record deleted successfully')
        
        # Redirect based on referer
        referer = request.META.get('HTTP_REFERER', '')
        if 'employee_attendance' in referer:
            return redirect('employee_attendance', employee_id=employee_id)
        return redirect('attendance_report')
    
    return render(request, 'attendance/confirm_delete.html', {
        'object': attendance,
        'title': 'Delete Attendance Record',
        'message': f'Are you sure you want to delete the attendance record for {attendance.employee.full_name} on {attendance.work_date}?'
    })

@login_required
@hr_required
def export_attendance(request, queryset=None):
    """Export attendance data to CSV"""
    # If queryset is not provided, build it from request params
    if queryset is None:
        department_id = request.GET.get('department', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        status = request.GET.get('status', '')
        
        query = Q()
        
        if date_from:
            query &= Q(work_date__gte=date_from)
        
        if date_to:
            query &= Q(work_date__lte=date_to)
        
        if status:
            query &= Q(status=status)
        
        if department_id:
            query &= Q(employee__department_id=department_id)
        
        queryset = Attendance.objects.filter(query).select_related(
            'employee', 'employee__department', 'shift'
        ).order_by('-work_date')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_export_{date.today()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Employee ID', 'Employee Name', 'Department', 'Date', 'Day',
        'Status', 'Time In', 'Time Out', 'Hours Worked', 'Overtime',
        'Shift', 'Notes'
    ])
    
    for record in queryset:
        writer.writerow([
            record.employee.employee_id,
            record.employee.full_name,
            record.employee.department.department_name if record.employee.department else '',
            record.work_date.strftime('%Y-%m-%d'),
            record.work_date.strftime('%A'),
            record.status,
            record.time_in.strftime('%H:%M') if record.time_in else '',
            record.time_out.strftime('%H:%M') if record.time_out else '',
            record.actual_work_hours or '',
            record.overtime_hours or '',
            record.shift.shift_name if record.shift else '',
            record.notes or ''
        ])
    
    return response

