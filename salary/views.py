from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
from django.utils import timezone
from django.template.loader import get_template
from django.core.paginator import Paginator
from datetime import date, datetime
import calendar
import csv
import io
import xlsxwriter
from weasyprint import HTML
from django.conf import settings
from .models import SalaryGrade, SeniorityAllowance, EmployeeSalaryGrade, SalaryAdvance, Salary
from .forms import *
from employee.models import Employee
from attendance.models import Attendance
from contract.models import EmploymentContract
from accounts.decorators import hr_required, check_module_permission



@login_required
@hr_required
def process_monthly_salary(request):
    """Process salary for all employees for a specific month and year"""
    if request.method == 'POST':
        month = int(request.POST.get('month'))
        year = int(request.POST.get('year'))
        
        # Check if already processed
        if Salary.objects.filter(month=month, year=year).exists():
            messages.warning(request, f'Salaries for {month}/{year} have already been processed.')
            return redirect('salary_list', month=month, year=year)
        
        # Get all active employees
        employees = Employee.objects.filter(status='Working')
        
        for employee in employees:
            # Get work days and overtime from attendance
            first_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])
            
            attendance_records = Attendance.objects.filter(
                employee=employee,
                work_date__gte=first_day,
                work_date__lte=last_day
            )
            
            work_days = attendance_records.filter(status='Present').count()
            leave_days = attendance_records.filter(status='On Leave').count()
            overtime_hours = attendance_records.aggregate(total=Sum('overtime_hours'))['total'] or 0
            
            # Get employee's current salary grade
            try:
                salary_grade = EmployeeSalaryGrade.objects.get(
                    employee=employee,
                    status='Active',
                    effective_date__lte=last_day
                )
                base_salary = salary_grade.grade.base_salary_amount
            except EmployeeSalaryGrade.DoesNotExist:
                # Use default salary from contract if no grade is assigned
                try:
                    contract = EmploymentContract.objects.filter(
                        employee=employee,
                        status='Active',
                        start_date__lte=last_day
                    ).order_by('-start_date').first()
                    base_salary = contract.base_salary if contract else 0
                except:
                    base_salary = 0
            
            # Calculate years of service for seniority allowance
            if employee.hire_date:
                service_years = (last_day - employee.hire_date).days // 365
                try:
                    seniority = SeniorityAllowance.objects.filter(
                        years_of_service__lte=service_years,
                        status=1
                    ).order_by('-years_of_service').first()
                    
                    seniority_allowance = (base_salary * seniority.allowance_percentage / 100) if seniority else 0
                except:
                    seniority_allowance = 0
            else:
                seniority_allowance = 0
            
            # Get any salary advances for this month/year
            advances = SalaryAdvance.objects.filter(
                employee=employee,
                deduction_month=month,
                deduction_year=year,
                status='Approved'
            )
            advance_amount = advances.aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate mandatory deductions (simplified example)
            social_insurance = base_salary * 0.08  # 8% for social insurance
            health_insurance = base_salary * 0.015  # 1.5% for health insurance
            unemployment_insurance = base_salary * 0.01  # 1% for unemployment insurance
            
            # Simple income tax calculation (would need more complex logic in real app)
            taxable_income = base_salary + seniority_allowance - social_insurance - health_insurance - unemployment_insurance
            if taxable_income <= 5000000:  # Example threshold
                income_tax = 0
            else:
                income_tax = (taxable_income - 5000000) * 0.1  # 10% on amount over threshold
            
            # Create salary record
            Salary.objects.create(
                employee=employee,
                month=month,
                year=year,
                work_days=work_days,
                leave_days=leave_days,
                overtime_hours=overtime_hours,
                base_salary=base_salary,
                seniority_allowance=seniority_allowance,
                income_tax=income_tax,
                social_insurance=social_insurance,
                health_insurance=health_insurance,
                unemployment_insurance=unemployment_insurance,
                advance=advance_amount,
                # Net salary will be calculated in model's save method
            )
        
        messages.success(request, f'Salaries for {month}/{year} processed successfully')
        return redirect('salary_list', month=month, year=year)
    
    # For GET request, show the form to select month/year
    current_month = date.today().month
    current_year = date.today().year
    
    return render(request, 'salary/process_monthly_salary.html', {
        'current_month': current_month,
        'current_year': current_year
    })

@login_required
@check_module_permission('salary', 'View')
def salary_list(request, month=None, year=None):
    """List salaries for a specific month and year"""
    if month is None:
        month = date.today().month
    if year is None:
        year = date.today().year
    
    salaries = Salary.objects.filter(month=month, year=year).order_by('employee__full_name')
    
    # Calculate summary statistics
    total_salaries = salaries.aggregate(
        total_base=Sum('base_salary'),
        total_net=Sum('net_salary'),
        total_tax=Sum('income_tax'),
        employee_count=Count('salary_id')
    )
    
    return render(request, 'salary/salary_list.html', {
        'salaries': salaries,
        'month': month,
        'year': year,
        'summary': total_salaries,
    })

@login_required
def salary_advance_request(request):
    """Create a new salary advance request (for employees)"""
    if not request.user.employee:
        messages.error(request, 'You do not have an employee profile')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = SalaryAdvanceForm(request.POST)
        if form.is_valid():
            advance = form.save(commit=False)
            advance.employee = request.user.employee
            advance.status = 'Pending'
            advance.save()
            
            messages.success(request, 'Salary advance request submitted successfully')
            return redirect('my_advances')
    else:
        form = SalaryAdvanceForm(initial={'advance_date': date.today()})
    
    return render(request, 'salary/salary_advance_form.html', {'form': form})

@login_required
@check_module_permission('salary', 'Edit')
def approve_salary_advance(request, pk):
    """Approve or reject salary advance request"""
    advance = get_object_or_404(SalaryAdvance, pk=pk)
    
    if advance.status != 'Pending':
        messages.error(request, 'This request is not pending approval')
        return redirect('pending_advances')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            advance.status = 'Approved'
            advance.approved_by = request.user.employee
            advance.approval_date = date.today()
            messages.success(request, 'Salary advance approved')
        elif action == 'reject':
            advance.status = 'Rejected'
            messages.success(request, 'Salary advance rejected')
        
        advance.save()
        return redirect('pending_advances')
    
    return render(request, 'salary/approve_advance.html', {'advance': advance})

@login_required
@check_module_permission('salary', 'View')
def export_salary_csv(request, month, year):
    """Export monthly salary data as CSV"""
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="salary_export_{month}_{year}.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    writer.writerow([
        'Employee ID', 'Employee Name', 'Department', 'Position',
        'Base Salary', 'Allowance', 'Seniority Allowance', 'Bonus',
        'Income Tax', 'Social Insurance', 'Health Insurance', 'Unemployment Insurance',
        'Deductions', 'Advance', 'Net Salary', 'Status'
    ])
    
    # Get data
    salaries = Salary.objects.filter(month=month, year=year).select_related('employee', 'employee__department', 'employee__position')
    
    for salary in salaries:
        writer.writerow([
            salary.employee.employee_id,
            salary.employee.full_name,
            salary.employee.department.department_name if salary.employee.department else '',
            salary.employee.position.position_name if salary.employee.position else '',
            salary.base_salary,
            salary.allowance,
            salary.seniority_allowance,
            salary.bonus,
            salary.income_tax,
            salary.social_insurance,
            salary.health_insurance,
            salary.unemployment_insurance,
            salary.deductions,
            salary.advance,
            salary.net_salary,
            'Paid' if salary.is_paid else 'Unpaid'
        ])
    
    return response


##################
# Salary Grades
##################

@login_required
@hr_required
def salary_grade_list(request):
    """List all salary grades"""
    grades = SalaryGrade.objects.all().order_by('-status', 'grade_name')
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    if status_filter:
        grades = grades.filter(status=status_filter)
    
    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        grades = grades.filter(
            Q(grade_name__icontains=search_query) | 
            Q(grade_code__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(grades, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'salary/salary_grade_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter
    })

@login_required
@hr_required
def salary_grade_create(request):
    """Create new salary grade"""
    if request.method == 'POST':
        form = SalaryGradeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salary grade created successfully')
            return redirect('salary_grade_list')
    else:
        form = SalaryGradeForm()
    
    return render(request, 'salary/salary_grade_form.html', {
        'form': form,
        'title': 'Create Salary Grade'
    })

@login_required
@hr_required
def salary_grade_update(request, pk):
    """Update existing salary grade"""
    grade = get_object_or_404(SalaryGrade, pk=pk)
    
    if request.method == 'POST':
        form = SalaryGradeForm(request.POST, instance=grade)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salary grade updated successfully')
            return redirect('salary_grade_list')
    else:
        form = SalaryGradeForm(instance=grade)
    
    return render(request, 'salary/salary_grade_form.html', {
        'form': form,
        'grade': grade,
        'title': 'Update Salary Grade'
    })

@login_required
@hr_required
def salary_grade_delete(request, pk):
    """Delete a salary grade"""
    grade = get_object_or_404(SalaryGrade, pk=pk)
    
    # Check if in use
    if EmployeeSalaryGrade.objects.filter(grade=grade).exists():
        messages.error(request, 'Cannot delete this grade as it is assigned to employees')
        return redirect('salary_grade_list')
    
    if request.method == 'POST':
        grade.delete()
        messages.success(request, 'Salary grade deleted successfully')
        return redirect('salary_grade_list')
    
    return render(request, 'salary/salary_grade_delete.html', {
        'grade': grade
    })

##################
# Seniority Allowance
##################

@login_required
@hr_required
def seniority_allowance_list(request):
    """List all seniority allowances"""
    allowances = SeniorityAllowance.objects.all().order_by('years_of_service')
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    if status_filter:
        allowances = allowances.filter(status=status_filter)
    
    return render(request, 'salary/seniority_allowance_list.html', {
        'allowances': allowances,
        'status_filter': status_filter
    })

@login_required
@hr_required
def seniority_allowance_create(request):
    """Create new seniority allowance"""
    if request.method == 'POST':
        form = SeniorityAllowanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Seniority allowance created successfully')
            return redirect('seniority_allowance_list')
    else:
        form = SeniorityAllowanceForm()
    
    return render(request, 'salary/seniority_allowance_form.html', {
        'form': form,
        'title': 'Create Seniority Allowance'
    })

@login_required
@hr_required
def seniority_allowance_update(request, pk):
    """Update existing seniority allowance"""
    allowance = get_object_or_404(SeniorityAllowance, pk=pk)
    
    if request.method == 'POST':
        form = SeniorityAllowanceForm(request.POST, instance=allowance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Seniority allowance updated successfully')
            return redirect('seniority_allowance_list')
    else:
        form = SeniorityAllowanceForm(instance=allowance)
    
    return render(request, 'salary/seniority_allowance_form.html', {
        'form': form,
        'allowance': allowance,
        'title': 'Update Seniority Allowance'
    })

@login_required
@hr_required
def seniority_allowance_delete(request, pk):
    """Delete a seniority allowance"""
    allowance = get_object_or_404(SeniorityAllowance, pk=pk)
    
    if request.method == 'POST':
        allowance.delete()
        messages.success(request, 'Seniority allowance deleted successfully')
        return redirect('seniority_allowance_list')
    
    return render(request, 'salary/seniority_allowance_delete.html', {
        'allowance': allowance
    })

##################
# Employee Salary Grade Assignments
##################

@login_required
@hr_required
def employee_salary_grade_list(request):
    """List all employee salary grade assignments"""
    assignments = EmployeeSalaryGrade.objects.all().select_related(
        'employee', 'grade', 'employee__department'
    ).order_by('-effective_date')
    
    # Get filter parameters
    employee_filter = request.GET.get('employee', '')
    status_filter = request.GET.get('status', '')
    department_filter = request.GET.get('department', '')
    
    if employee_filter:
        assignments = assignments.filter(employee_id=employee_filter)
    
    if status_filter:
        assignments = assignments.filter(status=status_filter)
    
    if department_filter:
        assignments = assignments.filter(employee__department_id=department_filter)
    
    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        assignments = assignments.filter(
            Q(employee__full_name__icontains=search_query) | 
            Q(grade__grade_name__icontains=search_query) |
            Q(decision_number__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(assignments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get list of employees and departments for filtering
    employees = Employee.objects.filter(status='Working').order_by('full_name')
    departments = Employee.objects.filter(status='Working').values_list(
        'department__department_id', 'department__department_name'
    ).distinct().exclude(department__isnull=True)
    
    return render(request, 'salary/employee_salary_grade_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'employee_filter': employee_filter,
        'department_filter': department_filter,
        'employees': employees,
        'departments': departments
    })

@login_required
@hr_required
def employee_salary_grade_create(request):
    """Assign salary grade to employee"""
    if request.method == 'POST':
        form = EmployeeSalaryGradeForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            
            # Check if employee has an active assignment
            active_assignment = EmployeeSalaryGrade.objects.filter(
                employee=assignment.employee,
                status='Active'
            ).first()
            
            if active_assignment:
                # End the current active assignment
                active_assignment.status = 'Inactive'
                active_assignment.end_date = assignment.effective_date - timezone.timedelta(days=1)
                active_assignment.save()
            
            assignment.save()
            messages.success(request, 'Salary grade assigned successfully')
            return redirect('employee_salary_grade_list')
    else:
        # Get employee ID from query parameter if provided
        employee_id = request.GET.get('employee')
        initial = {}
        if employee_id:
            try:
                initial['employee'] = Employee.objects.get(pk=employee_id)
                initial['effective_date'] = date.today()
            except Employee.DoesNotExist:
                pass
                
        form = EmployeeSalaryGradeForm(initial=initial)
    
    return render(request, 'salary/employee_salary_grade_form.html', {
        'form': form,
        'title': 'Assign Salary Grade'
    })

@login_required
@hr_required
def employee_salary_grade_update(request, pk):
    """Update employee salary grade assignment"""
    assignment = get_object_or_404(EmployeeSalaryGrade, pk=pk)
    
    if request.method == 'POST':
        form = EmployeeSalaryGradeForm(request.POST, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salary grade assignment updated successfully')
            return redirect('employee_salary_grade_list')
    else:
        form = EmployeeSalaryGradeForm(instance=assignment)
    
    return render(request, 'salary/employee_salary_grade_form.html', {
        'form': form,
        'assignment': assignment,
        'title': 'Update Salary Grade Assignment'
    })

@login_required
@hr_required
def employee_salary_grade_end(request, pk):
    """End an active salary grade assignment"""
    assignment = get_object_or_404(EmployeeSalaryGrade, pk=pk)
    
    if assignment.status != 'Active':
        messages.error(request, 'Only active assignments can be ended')
        return redirect('employee_salary_grade_list')
    
    if request.method == 'POST':
        end_date = request.POST.get('end_date')
        if not end_date:
            messages.error(request, 'End date is required')
        else:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                if end_date < assignment.effective_date:
                    messages.error(request, 'End date cannot be before effective date')
                    return render(request, 'salary/employee_salary_grade_end.html', {
                        'assignment': assignment
                    })
                
                assignment.end_date = end_date
                assignment.status = 'Inactive'
                assignment.save()
                
                messages.success(request, 'Salary grade assignment ended successfully')
                return redirect('employee_salary_grade_list')
            except ValueError:
                messages.error(request, 'Invalid date format')
    
    return render(request, 'salary/employee_salary_grade_end.html', {
        'assignment': assignment
    })

##################
# Salary Advances
##################

@login_required
def my_salary_advances(request):
    """View employee's own salary advances"""
    if not request.user.employee:
        messages.error(request, 'You do not have an employee profile')
        return redirect('dashboard')
    
    advances = SalaryAdvance.objects.filter(employee=request.user.employee).order_by('-advance_date')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        advances = advances.filter(status=status_filter)
    
    return render(request, 'salary/my_salary_advances.html', {
        'advances': advances,
        'status_filter': status_filter
    })

@login_required
@hr_required
def salary_advance_list(request):
    """List all salary advances"""
    advances = SalaryAdvance.objects.all().select_related(
        'employee', 'employee__department', 'approved_by'
    ).order_by('-advance_date')
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    department_filter = request.GET.get('department', '')
    month_filter = request.GET.get('month', '')
    year_filter = request.GET.get('year', '')
    
    if status_filter:
        advances = advances.filter(status=status_filter)
    
    if department_filter:
        advances = advances.filter(employee__department_id=department_filter)
    
    if month_filter and year_filter:
        try:
            month = int(month_filter)
            year = int(year_filter)
            advances = advances.filter(deduction_month=month, deduction_year=year)
        except (ValueError, TypeError):
            pass
    
    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        advances = advances.filter(
            Q(employee__full_name__icontains=search_query)
        )
    
    # Get departments for filtering
    departments = Employee.objects.filter(status='Working').values_list(
        'department__department_id', 'department__department_name'
    ).distinct().exclude(department__isnull=True)
    
    # Calculate totals
    total_pending = SalaryAdvance.objects.filter(status='Pending').aggregate(total=Sum('amount'))['total'] or 0
    total_approved = SalaryAdvance.objects.filter(status='Approved').aggregate(total=Sum('amount'))['total'] or 0
    
    return render(request, 'salary/salary_advance_list.html', {
        'advances': advances,
        'search_query': search_query,
        'status_filter': status_filter,
        'department_filter': department_filter,
        'month_filter': month_filter,
        'year_filter': year_filter,
        'departments': departments,
        'total_pending': total_pending,
        'total_approved': total_approved
    })

@login_required
@hr_required
def reject_salary_advance(request, pk):
    """Reject a salary advance request"""
    advance = get_object_or_404(SalaryAdvance, pk=pk)
    
    if advance.status != 'Pending':
        messages.error(request, 'This request is not pending approval')
        return redirect('salary_advance_list')
    
    if request.method == 'POST':
        advance.status = 'Rejected'
        advance.save()
        messages.success(request, 'Salary advance rejected successfully')
        return redirect('salary_advance_list')
    
    return render(request, 'salary/reject_salary_advance.html', {
        'advance': advance
    })

##################
# Salary Administration
##################

@login_required
@hr_required
def salary_admin(request):
    """Main salary administration dashboard"""
    # Get summary statistics
    today = date.today()
    current_month = today.month
    current_year = today.year
    
    # Active salary grades
    active_grades = SalaryGrade.objects.filter(status=1).count()
    
    # Salary statistics for current month
    salaries_this_month = Salary.objects.filter(month=current_month, year=current_year)
    total_paid = salaries_this_month.filter(is_paid=True).count()
    total_unpaid = salaries_this_month.filter(is_paid=False).count()
    
    # Total payroll amount for current month
    total_payroll = salaries_this_month.aggregate(total=Sum('net_salary'))['total'] or 0
    
    # Pending advance requests
    pending_advances = SalaryAdvance.objects.filter(status='Pending').count()
    
    # Get recent payments (last 5)
    recent_payments = Salary.objects.filter(
        is_paid=True
    ).select_related(
        'employee', 'employee__department'
    ).order_by('-payment_date')[:5]
    
    # Get monthly salaries for the current year
    monthly_data = []
    for month in range(1, 13):
        if month > current_month:
            break
        
        month_salaries = Salary.objects.filter(month=month, year=current_year)
        total_amount = month_salaries.aggregate(total=Sum('net_salary'))['total'] or 0
        
        monthly_data.append({
            'month': calendar.month_name[month],
            'total': total_amount,
            'count': month_salaries.count()
        })
    
    return render(request, 'salary/salary_admin.html', {
        'active_grades': active_grades,
        'total_paid': total_paid,
        'total_unpaid': total_unpaid,
        'total_payroll': total_payroll,
        'pending_advances': pending_advances,
        'recent_payments': recent_payments,
        'monthly_data': monthly_data,
        'current_month': calendar.month_name[current_month],
        'current_year': current_year
    })

@login_required
@hr_required
def salary_detail(request, pk):
    """View salary details"""
    salary = get_object_or_404(Salary, pk=pk)
    
    return render(request, 'salary/salary_detail.html', {
        'salary': salary
    })

@login_required
@hr_required
def salary_update(request, pk):
    """Update salary record"""
    salary = get_object_or_404(Salary, pk=pk)
    
    if request.method == 'POST':
        form = SalaryForm(request.POST, instance=salary)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salary record updated successfully')
            return redirect('salary_detail', pk=pk)
    else:
        form = SalaryForm(instance=salary)
    
    return render(request, 'salary/salary_update.html', {
        'form': form,
        'salary': salary
    })

@login_required
@hr_required
def mark_salary_paid(request, pk):
    """Mark a salary as paid"""
    salary = get_object_or_404(Salary, pk=pk)
    
    if salary.is_paid:
        messages.error(request, 'This salary has already been paid')
        return redirect('salary_detail', pk=pk)
    
    if request.method == 'POST':
        payment_date = request.POST.get('payment_date')
        payment_method = request.POST.get('payment_method')
        
        if not payment_date:
            messages.error(request, 'Payment date is required')
        else:
            try:
                payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
                
                salary.is_paid = True
                salary.payment_date = payment_date
                salary.notes = f"{salary.notes or ''}\n\nPaid on {payment_date} via {payment_method}"
                salary.save()
                
                messages.success(request, 'Salary marked as paid successfully')
                return redirect('salary_detail', pk=pk)
            except ValueError:
                messages.error(request, 'Invalid date format')
    
    today = date.today()
    
    return render(request, 'salary/mark_salary_paid.html', {
        'salary': salary,
        'today': today
    })

@login_required
@hr_required
def export_salary(request, year, month):
    """Export salary data"""
    export_format = request.GET.get('format', 'csv')
    
    salaries = Salary.objects.filter(
        year=year, month=month
    ).select_related(
        'employee', 'employee__department', 'employee__position'
    ).order_by('employee__full_name')
    
    if export_format == 'csv':
        return export_salary_csv(request, month, year)
    elif export_format == 'excel':
        return export_salary_excel(request, month, year, salaries)
    else:
        messages.error(request, 'Invalid export format')
        return redirect('salary_list', month=month, year=year)

def export_salary_excel(request, month, year, salaries):
    """Export salary data as Excel file"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('Salary Data')
    
    # Add headers
    headers = [
        'Employee ID', 'Employee Name', 'Department', 'Position',
        'Base Salary', 'Allowance', 'Seniority Allowance', 'Bonus',
        'Income Tax', 'Social Insurance', 'Health Insurance', 'Unemployment Insurance',
        'Deductions', 'Advance', 'Net Salary', 'Status'
    ]
    
    header_format = workbook.add_format({
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'fg_color': '#D7E4BC',
        'border': 1
    })
    
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # Add data
    row = 1
    for salary in salaries:
        worksheet.write(row, 0, salary.employee.employee_id)
        worksheet.write(row, 1, salary.employee.full_name)
        worksheet.write(row, 2, salary.employee.department.department_name if salary.employee.department else '')
        worksheet.write(row, 3, salary.employee.position.position_name if salary.employee.position else '')
        worksheet.write(row, 4, float(salary.base_salary))
        worksheet.write(row, 5, float(salary.allowance))
        worksheet.write(row, 6, float(salary.seniority_allowance))
        worksheet.write(row, 7, float(salary.bonus))
        worksheet.write(row, 8, float(salary.income_tax))
        worksheet.write(row, 9, float(salary.social_insurance))
        worksheet.write(row, 10, float(salary.health_insurance))
        worksheet.write(row, 11, float(salary.unemployment_insurance))
        worksheet.write(row, 12, float(salary.deductions))
        worksheet.write(row, 13, float(salary.advance))
        worksheet.write(row, 14, float(salary.net_salary))
        worksheet.write(row, 15, 'Paid' if salary.is_paid else 'Unpaid')
        row += 1
    
    # Set column widths
    worksheet.set_column(0, 0, 12)
    worksheet.set_column(1, 1, 30)
    worksheet.set_column(2, 3, 20)
    worksheet.set_column(4, 14, 15)
    worksheet.set_column(15, 15, 10)
    
    # Add summary at the bottom
    summary_format = workbook.add_format({
        'bold': True,
        'border': 1
    })
    
    worksheet.write(row + 1, 0, 'TOTALS', summary_format)
    worksheet.write_formula(row + 1, 4, f'=SUM(E2:E{row})', summary_format)
    worksheet.write_formula(row + 1, 14, f'=SUM(O2:O{row})', summary_format)
    
    workbook.close()
    
    # Create response
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="salary_export_{month}_{year}.xlsx"'
    
    return response

##################
# Employee Salary Views
##################

@login_required
def my_salary(request):
    """View employee's own salary information"""
    if not request.user.employee:
        messages.error(request, 'You do not have an employee profile')
        return redirect('dashboard')
    
    employee = request.user.employee
    
    # Get salary assignments
    salary_grades = EmployeeSalaryGrade.objects.filter(
        employee=employee
    ).select_related('grade').order_by('-effective_date')
    
    # Get salary history
    salary_history = Salary.objects.filter(
        employee=employee
    ).order_by('-year', '-month')
    
    # Group by year
    years = salary_history.values_list('year', flat=True).distinct().order_by('-year')
    grouped_history = {}
    
    for year in years:
        grouped_history[year] = []
        for month in range(12, 0, -1):
            try:
                salary = salary_history.get(year=year, month=month)
                grouped_history[year].append(salary)
            except Salary.DoesNotExist:
                continue
    
    # Get current salary grade
    current_grade = EmployeeSalaryGrade.objects.filter(
        employee=employee,
        status='Active'
    ).first()
    
    # Get latest salary
    latest_salary = salary_history.first()
    
    return render(request, 'salary/my_salary.html', {
        'employee': employee,
        'salary_grades': salary_grades,
        'grouped_history': grouped_history,
        'current_grade': current_grade,
        'latest_salary': latest_salary,
        'today': date.today()
    })

@login_required
def my_salary_detail(request, year, month):
    """View details of a specific salary"""
    if not request.user.employee:
        messages.error(request, 'You do not have an employee profile')
        return redirect('dashboard')
    
    try:
        salary = Salary.objects.get(
            employee=request.user.employee,
            year=year,
            month=month
        )
    except Salary.DoesNotExist:
        messages.error(request, f'No salary record found for {calendar.month_name[month]} {year}')
        return redirect('my_salary')
    
    return render(request, 'salary/my_salary_detail.html', {
        'salary': salary,
        'month_name': calendar.month_name[month]
    })

@login_required
def my_salary_payslip(request, salary_id):
    """Generate a payslip PDF for the employee"""
    if not request.user.employee:
        messages.error(request, 'You do not have an employee profile')
        return redirect('dashboard')
    
    try:
        salary = Salary.objects.get(
            salary_id=salary_id,
            employee=request.user.employee
        )
    except Salary.DoesNotExist:
        messages.error(request, 'Salary record not found')
        return redirect('my_salary')
    
    # Prepare template context
    context = {
        'salary': salary,
        'employee': request.user.employee,
        'month_name': calendar.month_name[salary.month],
        'year': salary.year,
        'company_name': 'Your Company Name',
        'company_address': 'Your Company Address',
        'company_logo': f"{settings.STATIC_URL}img/logo.png",
        'today': date.today()
    }
    
    # Generate PDF
    template = get_template('salary/payslip_pdf.html')
    html_string = template.render(context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf_file = html.write_pdf()
    
    # Create response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"payslip_{request.user.employee.full_name}_{salary.month}_{salary.year}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response