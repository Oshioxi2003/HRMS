from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Avg, Sum, Q, F, Case, When, Value, IntegerField, Min, Max
from django.db.models.functions import TruncMonth, TruncYear
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import date, datetime, timedelta
import json
import csv
import tempfile
import calendar
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import numpy as np
import xlsxwriter
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape
from reportlab.platypus import Spacer

from .models import HRReport, AnalyticsData
from .forms import *
from employee.models import *
from attendance.models import *
from leave.models import *
from salary.models import *
from performance.models import *
from contract.models import *
from assets.models import *
from expenses.models import *
from accounts.decorators import *



@login_required
@check_module_permission('reports', 'View')
def hr_reports(request):
    """Main reports dashboard page"""
    # Get recent saved reports
    recent_reports = HRReport.objects.all().order_by('-created_date')[:5]
    
    # Employee statistics
    total_employees = Employee.objects.filter(status='Working').count()
    departments = Department.objects.filter(status=1)
    dept_stats = []
    for dept in departments:
        count = Employee.objects.filter(department=dept, status='Working').count()
        dept_stats.append({
            'name': dept.department_name,
            'count': count
        })
    
    # Get report counts by type
    report_counts = HRReport.objects.values('report_type').annotate(count=Count('report_id'))
    
    context = {
        'recent_reports': recent_reports,
        'report_counts': report_counts,
        'total_employees': total_employees,
        'dept_stats': dept_stats
    }
    
    return render(request, 'reports/reports_dashboard.html', context)

@login_required
@check_module_permission('reports', 'View')
def employee_report(request):
    """Generate employee reports"""
    if request.method == 'POST':
        form = EmployeeReportForm(request.POST)
        if form.is_valid():
            # Get form data
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            department = form.cleaned_data['department']
            position = form.cleaned_data['position']
            status = form.cleaned_data['status']
            report_type = form.cleaned_data['report_type']
            export_format = form.cleaned_data['export_format']
            
            # Build query
            query = Q()
            if department:
                query &= Q(department=department)
            if position:
                query &= Q(position=position)
            if status:
                query &= Q(status=status)
            
            # Get employee data
            employees = Employee.objects.filter(query).select_related('department', 'position')
            
            # Handle export if requested
            if 'export' in request.POST:
                return export_employee_report(
                    employees, report_type, export_format, start_date, end_date, department
                )
            
            # Prepare context for display in template
            context = {
                'form': form,
                'employees': employees,
                'report_type': report_type,
                'start_date': start_date,
                'end_date': end_date,
                'department': department,
                'position': position,
                'status': status,
                'employee_count': employees.count(),
                'show_results': True
            }
            
            # Additional data for summary report
            if report_type == 'summary':
                gender_stats = employees.values('gender').annotate(count=Count('employee_id'))
                dept_stats = employees.values('department__department_name').annotate(count=Count('employee_id'))
                position_stats = employees.values('position__position_name').annotate(count=Count('employee_id'))
                
                context.update({
                    'gender_stats': gender_stats,
                    'dept_stats': dept_stats,
                    'position_stats': position_stats
                })
            
            # Additional data for turnover report
            if report_type == 'turnover':
                # Calculate new hires in period
                new_hires = Employee.objects.filter(
                    hire_date__gte=start_date,
                    hire_date__lte=end_date
                ).count()
                
                # Calculate separations in period
                separations = Employee.objects.filter(
                    status='Resigned',
                    updated_date__gte=start_date,
                    updated_date__lte=end_date
                ).count()
                
                # Calculate turnover rate
                avg_headcount = (
                    Employee.objects.filter(hire_date__lte=start_date).count() +
                    Employee.objects.filter(hire_date__lte=end_date).count()
                ) / 2
                
                turnover_rate = (separations / avg_headcount * 100) if avg_headcount > 0 else 0
                
                context.update({
                    'new_hires': new_hires,
                    'separations': separations,
                    'turnover_rate': round(turnover_rate, 2),
                    'avg_headcount': round(avg_headcount)
                })
            
            return render(request, 'reports/employee_report.html', context)
    else:
        # Initialize form with default dates (current month)
        today = date.today()
        first_day = date(today.year, today.month, 1)
        last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        form = EmployeeReportForm(initial={
            'start_date': first_day,
            'end_date': last_day
        })
    
    return render(request, 'reports/employee_report.html', {'form': form})

def export_employee_report(employees, report_type, export_format, start_date, end_date, department=None):
    """Export employee report in requested format"""
    if export_format == 'pdf':
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="employee_report_{start_date}_to_{end_date}.pdf"'
        
        # Create PDF document
        doc = SimpleDocTemplate(response, pagesize=A4)
        styles = getSampleStyleSheet()
        
        # Define content
        content = []
        
        # Title
        report_title = f"Employee Report: {start_date} to {end_date}"
        if department:
            report_title += f" - {department.department_name} Department"
        content.append(Paragraph(report_title, styles['Title']))
        content.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        content.append(Paragraph(f"Total Employees: {employees.count()}", styles['Normal']))
        
        # Table data
        if report_type == 'detailed':
            table_data = [['ID', 'Name', 'Department', 'Position', 'Gender', 'Hire Date', 'Status']]
            for employee in employees:
                table_data.append([
                    employee.employee_id,
                    employee.full_name,
                    employee.department.department_name if employee.department else 'N/A',
                    employee.position.position_name if employee.position else 'N/A',
                    employee.gender or 'N/A',
                    employee.hire_date.strftime('%Y-%m-%d') if employee.hire_date else 'N/A',
                    employee.status
                ])
            
            # Create table
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            content.append(table)
        
        # Add summary data if it's a summary report
        elif report_type == 'summary':
            # Gender distribution
            gender_stats = employees.values('gender').annotate(count=Count('employee_id'))
            
            content.append(Paragraph("Gender Distribution", styles['Heading2']))
            gender_data = [['Gender', 'Count']]
            for stat in gender_stats:
                gender_data.append([stat['gender'] or 'Not Specified', stat['count']])
            
            gender_table = Table(gender_data)
            gender_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            content.append(gender_table)
            
            # Department distribution
            dept_stats = employees.values('department__department_name').annotate(count=Count('employee_id'))
            
            content.append(Paragraph("Department Distribution", styles['Heading2']))
            dept_data = [['Department', 'Count']]
            for stat in dept_stats:
                dept_data.append([stat['department__department_name'] or 'Not Assigned', stat['count']])
            
            dept_table = Table(dept_data)
            dept_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            content.append(dept_table)
        
        # Build PDF
        doc.build(content)
        return response
    
    elif export_format == 'excel':
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#3f51b5',
            'color': 'white',
            'border': 1
        })
        
        # Write headers
        headers = ['ID', 'Name', 'Department', 'Position', 'Gender', 'Hire Date', 'Status']
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)
        
        # Write data rows
        for row_num, employee in enumerate(employees, 1):
            worksheet.write(row_num, 0, employee.employee_id)
            worksheet.write(row_num, 1, employee.full_name)
            worksheet.write(row_num, 2, employee.department.department_name if employee.department else 'N/A')
            worksheet.write(row_num, 3, employee.position.position_name if employee.position else 'N/A')
            worksheet.write(row_num, 4, employee.gender or 'N/A')
            worksheet.write(row_num, 5, employee.hire_date.strftime('%Y-%m-%d') if employee.hire_date else 'N/A')
            worksheet.write(row_num, 6, employee.status)
        
        # Auto-adjust column widths
        for col_num in range(len(headers)):
            worksheet.set_column(col_num, col_num, 15)
        
        # Add summary sheet if it's a summary report
        if report_type == 'summary':
            summary_sheet = workbook.add_worksheet('Summary')
            
            # Add title
            summary_sheet.write(0, 0, 'Employee Report Summary', workbook.add_format({'bold': True, 'font_size': 14}))
            summary_sheet.write(1, 0, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            summary_sheet.write(2, 0, f"Total Employees: {employees.count()}")
            
            # Gender distribution
            gender_stats = employees.values('gender').annotate(count=Count('employee_id'))
            
            summary_sheet.write(4, 0, 'Gender Distribution', workbook.add_format({'bold': True}))
            summary_sheet.write(5, 0, 'Gender', header_format)
            summary_sheet.write(5, 1, 'Count', header_format)
            
            row = 6
            for stat in gender_stats:
                summary_sheet.write(row, 0, stat['gender'] or 'Not Specified')
                summary_sheet.write(row, 1, stat['count'])
                row += 1
            
            # Add chart
            gender_chart = workbook.add_chart({'type': 'pie'})
            gender_chart.add_series({
                'name': 'Gender Distribution',
                'categories': ['Summary', 6, 0, row-1, 0],
                'values': ['Summary', 6, 1, row-1, 1],
            })
            gender_chart.set_title({'name': 'Gender Distribution'})
            summary_sheet.insert_chart('D5', gender_chart, {'x_offset': 25, 'y_offset': 10})
            
            # Department distribution
            dept_stats = employees.values('department__department_name').annotate(count=Count('employee_id'))
            
            summary_sheet.write(row+2, 0, 'Department Distribution', workbook.add_format({'bold': True}))
            summary_sheet.write(row+3, 0, 'Department', header_format)
            summary_sheet.write(row+3, 1, 'Count', header_format)
            
            dept_row = row+4
            for stat in dept_stats:
                summary_sheet.write(dept_row, 0, stat['department__department_name'] or 'Not Assigned')
                summary_sheet.write(dept_row, 1, stat['count'])
                dept_row += 1
            
            # Auto-adjust columns
            summary_sheet.set_column(0, 0, 25)
            summary_sheet.set_column(1, 1, 15)
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="employee_report_{start_date}_to_{end_date}.xlsx"'
        return response
    
    elif export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="employee_report_{start_date}_to_{end_date}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Name', 'Department', 'Position', 'Gender', 'Hire Date', 'Status'])
        
        for employee in employees:
            writer.writerow([
                employee.employee_id,
                employee.full_name,
                employee.department.department_name if employee.department else 'N/A',
                employee.position.position_name if employee.position else 'N/A',
                employee.gender or 'N/A',
                employee.hire_date.strftime('%Y-%m-%d') if employee.hire_date else 'N/A',
                employee.status
            ])
        
        return response

@login_required
@check_module_permission('reports', 'View')
def employee_turnover_report(request):
    """Generate employee turnover report"""
    # Get date range from request
    year = request.GET.get('year', date.today().year)
    
    # Convert to integer
    try:
        year = int(year)
    except ValueError:
        year = date.today().year
    
    # Calculate turnover rate by month
    turnover_data = []
    for month in range(1, 13):
        # Start with first day of the month
        month_start = date(year, month, 1)
        
        # Get last day of the month
        if month == 12:
            next_month_start = date(year + 1, 1, 1)
        else:
            next_month_start = date(year, month + 1, 1)
        month_end = next_month_start - timedelta(days=1)
        
        # Skip future months
        if month_start > date.today():
            continue
        
        # Get employee count at beginning of month
        beginning_count = Employee.objects.filter(
            hire_date__lt=month_start
        ).exclude(
            status='Resigned',
            updated_date__lt=month_start
        ).count()
        
        # Get new hires during the month
        new_hires = Employee.objects.filter(
            hire_date__gte=month_start,
            hire_date__lte=month_end
        ).count()
        
        # Get separations during the month
        separations = Employee.objects.filter(
            status='Resigned',
            updated_date__gte=month_start,
            updated_date__lte=month_end
        ).count()
        
        # Calculate turnover rate
        if beginning_count > 0:
            turnover_rate = (separations / beginning_count) * 100
        else:
            turnover_rate = 0
        
        turnover_data.append({
            'month': month,
            'month_name': month_start.strftime('%B'),
            'beginning_count': beginning_count,
            'new_hires': new_hires,
            'separations': separations,
            'ending_count': beginning_count + new_hires - separations,
            'turnover_rate': round(turnover_rate, 2)
        })
    
    # Get available years for filter
    min_year = Employee.objects.order_by('hire_date').values_list('hire_date', flat=True).first()
    available_years = []
    if min_year:
        min_year = min_year.year
        current_year = date.today().year
        available_years = list(range(min_year, current_year + 1))
    
    context = {
        'turnover_data': turnover_data,
        'selected_year': year,
        'available_years': available_years
    }
    
    # Check if export to CSV is requested
    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="employee_turnover_{year}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Month', 'Beginning Count', 'New Hires', 'Separations', 'Ending Count', 'Turnover Rate (%)'])
        
        for data in turnover_data:
            writer.writerow([
                data['month_name'],
                data['beginning_count'],
                data['new_hires'],
                data['separations'],
                data['ending_count'],
                data['turnover_rate']
            ])
        
        return response
    
    return render(request, 'reports/employee_turnover.html', context)

@login_required
@check_module_permission('reports', 'View')
def headcount_report(request):
    """Generate headcount report by department and position"""
    today = date.today()
    
    # Get date range from request
    date_str = request.GET.get('date', today.strftime('%Y-%m-%d'))
    
    try:
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        report_date = today
    
    # Get headcount by department
    dept_headcount = Employee.objects.filter(
        status='Working',
        hire_date__lte=report_date
    ).exclude(
        status='Resigned',
        updated_date__lt=report_date
    ).values('department__department_name').annotate(count=Count('employee_id')).order_by('-count')
    
    # Get headcount by position
    position_headcount = Employee.objects.filter(
        status='Working',
        hire_date__lte=report_date
    ).exclude(
        status='Resigned',
        updated_date__lt=report_date
    ).values('position__position_name').annotate(count=Count('employee_id')).order_by('-count')
    
    # Get total headcount
    total_headcount = Employee.objects.filter(
        status='Working',
        hire_date__lte=report_date
    ).exclude(
        status='Resigned',
        updated_date__lt=report_date
    ).count()
    
    # Get gender distribution
    gender_distribution = Employee.objects.filter(
        status='Working',
        hire_date__lte=report_date
    ).exclude(
        status='Resigned',
        updated_date__lt=report_date
    ).values('gender').annotate(count=Count('employee_id'))
    
    context = {
        'dept_headcount': dept_headcount,
        'position_headcount': position_headcount,
        'total_headcount': total_headcount,
        'gender_distribution': gender_distribution,
        'report_date': report_date
    }
    
    # Check if export is requested
    if 'export' in request.GET:
        export_format = request.GET.get('format', 'excel')
        
        if export_format == 'excel':
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output)
            
            # Department sheet
            dept_sheet = workbook.add_worksheet('Departments')
            dept_sheet.write(0, 0, f'Headcount by Department as of {report_date}', workbook.add_format({'bold': True, 'font_size': 14}))
            dept_sheet.write(2, 0, 'Department', workbook.add_format({'bold': True}))
            dept_sheet.write(2, 1, 'Headcount', workbook.add_format({'bold': True}))
            
            for i, dept in enumerate(dept_headcount, 3):
                dept_sheet.write(i, 0, dept['department__department_name'] or 'Not Assigned')
                dept_sheet.write(i, 1, dept['count'])
            
            # Add chart
            dept_chart = workbook.add_chart({'type': 'bar'})
            dept_chart.add_series({
                'name': 'Headcount',
                'categories': ['Departments', 3, 0, 3 + len(dept_headcount) - 1, 0],
                'values': ['Departments', 3, 1, 3 + len(dept_headcount) - 1, 1],
            })
            dept_chart.set_title({'name': 'Headcount by Department'})
            dept_chart.set_x_axis({'name': 'Headcount'})
            dept_chart.set_y_axis({'name': 'Department'})
            dept_sheet.insert_chart('D2', dept_chart, {'x_scale': 1.5, 'y_scale': 2})
            
            # Position sheet
            pos_sheet = workbook.add_worksheet('Positions')
            pos_sheet.write(0, 0, f'Headcount by Position as of {report_date}', workbook.add_format({'bold': True, 'font_size': 14}))
            pos_sheet.write(2, 0, 'Position', workbook.add_format({'bold': True}))
            pos_sheet.write(2, 1, 'Headcount', workbook.add_format({'bold': True}))
            
            for i, pos in enumerate(position_headcount, 3):
                pos_sheet.write(i, 0, pos['position__position_name'] or 'Not Assigned')
                pos_sheet.write(i, 1, pos['count'])
            
            # Gender sheet
            gender_sheet = workbook.add_worksheet('Gender')
            gender_sheet.write(0, 0, f'Headcount by Gender as of {report_date}', workbook.add_format({'bold': True, 'font_size': 14}))
            gender_sheet.write(2, 0, 'Gender', workbook.add_format({'bold': True}))
            gender_sheet.write(2, 1, 'Headcount', workbook.add_format({'bold': True}))
            
            for i, gender in enumerate(gender_distribution, 3):
                gender_sheet.write(i, 0, gender['gender'] or 'Not Specified')
                gender_sheet.write(i, 1, gender['count'])
            
            # Add gender chart
            gender_chart = workbook.add_chart({'type': 'pie'})
            gender_chart.add_series({
                'name': 'Gender Distribution',
                'categories': ['Gender', 3, 0, 3 + len(gender_distribution) - 1, 0],
                'values': ['Gender', 3, 1, 3 + len(gender_distribution) - 1, 1],
            })
            gender_chart.set_title({'name': 'Gender Distribution'})
            gender_sheet.insert_chart('D2', gender_chart)
            
            # Summary sheet
            summary_sheet = workbook.add_worksheet('Summary')
            summary_sheet.write(0, 0, f'Headcount Summary as of {report_date}', workbook.add_format({'bold': True, 'font_size': 14}))
            summary_sheet.write(2, 0, 'Total Headcount', workbook.add_format({'bold': True}))
            summary_sheet.write(2, 1, total_headcount)
            
            workbook.close()
            output.seek(0)
            
            response = HttpResponse(
                output,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="headcount_report_{report_date}.xlsx"'
            return response
    
    return render(request, 'reports/headcount_report.html', context)

@login_required
@check_module_permission('reports', 'View')
def attendance_summary_report(request):
    """Generate attendance summary report"""
    if request.method == 'POST':
        form = AttendanceReportForm(request.POST)
        if form.is_valid():
            # Get form data
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            department = form.cleaned_data['department']
            report_type = form.cleaned_data['report_type']
            export_format = form.cleaned_data['export_format']
            
            # Build query for employees
            employee_query = Q(status='Working')
            if department:
                employee_query &= Q(department=department)
            
            employees = Employee.objects.filter(employee_query)
            
            # Get attendance data
            attendance_query = Q(work_date__gte=start_date, work_date__lte=end_date)
            
            if report_type == 'absent':
                attendance_query &= Q(status='Absent')
            elif report_type == 'overtime':
                attendance_query &= Q(overtime_hours__gt=0)
            
            attendances = Attendance.objects.filter(attendance_query)
            
            # Handle export if requested
            if 'export' in request.POST:
                return export_attendance_report(
                    attendances, employees, report_type, export_format, start_date, end_date, department
                )
            
            # Create summary data
            summary_data = {}
            
            total_days = (end_date - start_date).days + 1
            workdays = 0
            
            # Count workdays (excluding weekends)
            current_date = start_date
            while current_date <= end_date:
                if current_date.weekday() < 5:  # 0-4 are Monday-Friday
                    workdays += 1
                current_date += timedelta(days=1)
            
            # Overall statistics
            total_attendance = attendances.count()
            present_count = attendances.filter(status='Present').count()
            absent_count = attendances.filter(status='Absent').count()
            leave_count = attendances.filter(status='On Leave').count()
            
            # Attendance by date
            attendance_by_date = (
                attendances
                .values('work_date')
                .annotate(
                    present=Count('attendance_id', filter=Q(status='Present')),
                    absent=Count('attendance_id', filter=Q(status='Absent')),
                    on_leave=Count('attendance_id', filter=Q(status='On Leave')),
                    total=Count('attendance_id')
                )
                .order_by('work_date')
            )
            
            # Attendance by employee
            if report_type == 'detailed':
                employee_attendance = []
                
                for employee in employees:
                    emp_attendances = attendances.filter(employee=employee)
                    
                    present = emp_attendances.filter(status='Present').count()
                    absent = emp_attendances.filter(status='Absent').count()
                    on_leave = emp_attendances.filter(status='On Leave').count()
                    
                    attendance_rate = (present / workdays * 100) if workdays > 0 else 0
                    
                    employee_attendance.append({
                        'employee': employee,
                        'present': present,
                        'absent': absent,
                        'on_leave': on_leave,
                        'attendance_rate': round(attendance_rate, 2)
                    })
                
                # Sort by attendance rate (descending)
                employee_attendance.sort(key=lambda x: x['attendance_rate'], reverse=True)
                
                context = {
                    'form': form,
                    'start_date': start_date,
                    'end_date': end_date,
                    'department': department,
                    'report_type': report_type,
                    'workdays': workdays,
                    'total_attendance': total_attendance,
                    'present_count': present_count,
                    'absent_count': absent_count,
                    'leave_count': leave_count,
                    'attendance_by_date': attendance_by_date,
                    'employee_attendance': employee_attendance,
                    'show_results': True
                }
            else:
                context = {
                    'form': form,
                    'start_date': start_date,
                    'end_date': end_date,
                    'department': department,
                    'report_type': report_type,
                    'workdays': workdays,
                    'total_attendance': total_attendance,
                    'present_count': present_count,
                    'absent_count': absent_count,
                    'leave_count': leave_count,
                    'attendance_by_date': attendance_by_date,
                    'show_results': True
                }
            
            return render(request, 'reports/attendance_summary.html', context)
    else:
        # Initialize form with default dates (current month)
        today = date.today()
        first_day = date(today.year, today.month, 1)
        last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        form = AttendanceReportForm(initial={
            'start_date': first_day,
            'end_date': last_day
        })
    
    return render(request, 'reports/attendance_summary.html', {'form': form})

def export_attendance_report(attendances, employees, report_type, export_format, start_date, end_date, department=None):
    """Export attendance report in requested format"""
    # Calculate workdays
    workdays = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:  # 0-4 are Monday-Friday
            workdays += 1
        current_date += timedelta(days=1)
    
    if export_format == 'excel':
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#3f51b5',
            'color': 'white',
            'border': 1
        })
        
        # Create summary worksheet
        summary_sheet = workbook.add_worksheet('Summary')
        
        # Add title
        title = f"Attendance Report: {start_date} to {end_date}"
        if department:
            title += f" - {department.department_name} Department"
        
        summary_sheet.write(0, 0, title, workbook.add_format({'bold': True, 'font_size': 14}))
        summary_sheet.write(1, 0, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Add summary statistics
        summary_sheet.write(3, 0, "Summary Statistics", workbook.add_format({'bold': True}))
        summary_sheet.write(4, 0, "Total Work Days:")
        summary_sheet.write(4, 1, workdays)
        
        summary_sheet.write(5, 0, "Present:")
        summary_sheet.write(5, 1, attendances.filter(status='Present').count())
        
        summary_sheet.write(6, 0, "Absent:")
        summary_sheet.write(6, 1, attendances.filter(status='Absent').count())
        
        summary_sheet.write(7, 0, "On Leave:")
        summary_sheet.write(7, 1, attendances.filter(status='On Leave').count())
        
        # Add data by date
        summary_sheet.write(9, 0, "Attendance by Date", workbook.add_format({'bold': True}))
        summary_sheet.write(10, 0, "Date", header_format)
        summary_sheet.write(10, 1, "Present", header_format)
        summary_sheet.write(10, 2, "Absent", header_format)
        summary_sheet.write(10, 3, "On Leave", header_format)
        summary_sheet.write(10, 4, "Total", header_format)
        
        attendance_by_date = (
            attendances
            .values('work_date')
            .annotate(
                present=Count('attendance_id', filter=Q(status='Present')),
                absent=Count('attendance_id', filter=Q(status='Absent')),
                on_leave=Count('attendance_id', filter=Q(status='On Leave')),
                total=Count('attendance_id')
            )
            .order_by('work_date')
        )
        
        for i, data in enumerate(attendance_by_date, 11):
            summary_sheet.write(i, 0, data['work_date'].strftime('%Y-%m-%d'))
            summary_sheet.write(i, 1, data['present'])
            summary_sheet.write(i, 2, data['absent'])
            summary_sheet.write(i, 3, data['on_leave'])
            summary_sheet.write(i, 4, data['total'])
        
        # Add chart
        chart = workbook.add_chart({'type': 'column'})
        chart.add_series({
            'name': 'Present',
            'categories': ['Summary', 11, 0, 10 + len(attendance_by_date), 0],
            'values': ['Summary', 11, 1, 10 + len(attendance_by_date), 1],
        })
        chart.add_series({
            'name': 'Absent',
            'categories': ['Summary', 11, 0, 10 + len(attendance_by_date), 0],
            'values': ['Summary', 11, 2, 10 + len(attendance_by_date), 2],
        })
        chart.add_series({
            'name': 'On Leave',
            'categories': ['Summary', 11, 0, 10 + len(attendance_by_date), 0],
            'values': ['Summary', 11, 3, 10 + len(attendance_by_date), 3],
        })
        
        chart.set_title({'name': 'Attendance by Date'})
        chart.set_x_axis({'name': 'Date'})
        chart.set_y_axis({'name': 'Count'})
        
        summary_sheet.insert_chart('G10', chart, {'x_scale': 1.5, 'y_scale': 1.5})
        
        # Create detailed worksheet if it's a detailed report
        if report_type == 'detailed':
            detail_sheet = workbook.add_worksheet('Employee Details')
            
            # Add headers
            detail_sheet.write(0, 0, 'Employee ID', header_format)
            detail_sheet.write(0, 1, 'Name', header_format)
            detail_sheet.write(0, 2, 'Department', header_format)
            detail_sheet.write(0, 3, 'Present Days', header_format)
            detail_sheet.write(0, 4, 'Absent Days', header_format)
            detail_sheet.write(0, 5, 'Leave Days', header_format)
            detail_sheet.write(0, 6, 'Attendance Rate (%)', header_format)
            
            row = 1
            for employee in employees:
                emp_attendances = attendances.filter(employee=employee)
                
                present = emp_attendances.filter(status='Present').count()
                absent = emp_attendances.filter(status='Absent').count()
                on_leave = emp_attendances.filter(status='On Leave').count()
                
                attendance_rate = (present / workdays * 100) if workdays > 0 else 0
                
                detail_sheet.write(row, 0, employee.employee_id)
                detail_sheet.write(row, 1, employee.full_name)
                detail_sheet.write(row, 2, employee.department.department_name if employee.department else 'N/A')
                detail_sheet.write(row, 3, present)
                detail_sheet.write(row, 4, absent)
                detail_sheet.write(row, 5, on_leave)
                detail_sheet.write(row, 6, round(attendance_rate, 2))
                
                row += 1
            
            # Auto-adjust column widths
            detail_sheet.set_column(0, 0, 12)
            detail_sheet.set_column(1, 1, 25)
            detail_sheet.set_column(2, 2, 20)
            detail_sheet.set_column(3, 6, 15)
        
        # Create absence worksheet if it's an absence report
        elif report_type == 'absent':
            absent_sheet = workbook.add_worksheet('Absences')
            
            # Add headers
            absent_sheet.write(0, 0, 'Employee ID', header_format)
            absent_sheet.write(0, 1, 'Name', header_format)
            absent_sheet.write(0, 2, 'Department', header_format)
            absent_sheet.write(0, 3, 'Absence Date', header_format)
            absent_sheet.write(0, 4, 'Notes', header_format)
            
            row = 1
            absences = attendances.filter(status='Absent').select_related('employee')
            
            for absence in absences:
                absent_sheet.write(row, 0, absence.employee.employee_id)
                absent_sheet.write(row, 1, absence.employee.full_name)
                absent_sheet.write(row, 2, absence.employee.department.department_name if absence.employee.department else 'N/A')
                absent_sheet.write(row, 3, absence.work_date.strftime('%Y-%m-%d'))
                absent_sheet.write(row, 4, absence.notes or '')
                
                row += 1
            
            # Auto-adjust column widths
            absent_sheet.set_column(0, 0, 12)
            absent_sheet.set_column(1, 1, 25)
            absent_sheet.set_column(2, 2, 20)
            absent_sheet.set_column(3, 3, 15)
            absent_sheet.set_column(4, 4, 30)
        
        # Create overtime worksheet if it's an overtime report
        elif report_type == 'overtime':
            overtime_sheet = workbook.add_worksheet('Overtime')
            
            # Add headers
            overtime_sheet.write(0, 0, 'Employee ID', header_format)
            overtime_sheet.write(0, 1, 'Name', header_format)
            overtime_sheet.write(0, 2, 'Department', header_format)
            overtime_sheet.write(0, 3, 'Date', header_format)
            overtime_sheet.write(0, 4, 'Overtime Hours', header_format)
            
            row = 1
            overtimes = attendances.filter(overtime_hours__gt=0).select_related('employee')
            
            for overtime in overtimes:
                overtime_sheet.write(row, 0, overtime.employee.employee_id)
                overtime_sheet.write(row, 1, overtime.employee.full_name)
                overtime_sheet.write(row, 2, overtime.employee.department.department_name if overtime.employee.department else 'N/A')
                overtime_sheet.write(row, 3, overtime.work_date.strftime('%Y-%m-%d'))
                overtime_sheet.write(row, 4, float(overtime.overtime_hours))
                
                row += 1
            
            # Summary by employee
            overtime_sheet.write(row + 2, 0, 'Overtime Summary by Employee', workbook.add_format({'bold': True}))
            overtime_sheet.write(row + 3, 0, 'Employee ID', header_format)
            overtime_sheet.write(row + 3, 1, 'Name', header_format)
            overtime_sheet.write(row + 3, 2, 'Department', header_format)
            overtime_sheet.write(row + 3, 3, 'Total Overtime Hours', header_format)
            
            overtime_by_employee = (
                attendances
                .filter(overtime_hours__gt=0)
                .values('employee__employee_id', 'employee__full_name', 'employee__department__department_name')
                .annotate(total_overtime=Sum('overtime_hours'))
                .order_by('-total_overtime')
            )
            
            summary_row = row + 4
            for emp_overtime in overtime_by_employee:
                overtime_sheet.write(summary_row, 0, emp_overtime['employee__employee_id'])
                overtime_sheet.write(summary_row, 1, emp_overtime['employee__full_name'])
                overtime_sheet.write(summary_row, 2, emp_overtime['employee__department__department_name'] or 'N/A')
                overtime_sheet.write(summary_row, 3, float(emp_overtime['total_overtime']))
                
                summary_row += 1
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"attendance_report_{start_date}_to_{end_date}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    elif export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="attendance_report_{start_date}_to_{end_date}.csv"'
        
        writer = csv.writer(response)
        
        if report_type == 'detailed':
            writer.writerow(['Employee ID', 'Employee Name', 'Department', 'Present Days', 'Absent Days', 'Leave Days', 'Attendance Rate (%)'])
            
            for employee in employees:
                emp_attendances = attendances.filter(employee=employee)
                
                present = emp_attendances.filter(status='Present').count()
                absent = emp_attendances.filter(status='Absent').count()
                on_leave = emp_attendances.filter(status='On Leave').count()
                
                attendance_rate = (present / workdays * 100) if workdays > 0 else 0
                
                writer.writerow([
                    employee.employee_id,
                    employee.full_name,
                    employee.department.department_name if employee.department else 'N/A',
                    present,
                    absent,
                    on_leave,
                    round(attendance_rate, 2)
                ])
        elif report_type == 'summary':
            writer.writerow(['Date', 'Present', 'Absent', 'On Leave', 'Total'])
            
            attendance_by_date = (
                attendances
                .values('work_date')
                .annotate(
                    present=Count('attendance_id', filter=Q(status='Present')),
                    absent=Count('attendance_id', filter=Q(status='Absent')),
                    on_leave=Count('attendance_id', filter=Q(status='On Leave')),
                    total=Count('attendance_id')
                )
                .order_by('work_date')
            )
            
            for data in attendance_by_date:
                writer.writerow([
                    data['work_date'].strftime('%Y-%m-%d'),
                    data['present'],
                    data['absent'],
                    data['on_leave'],
                    data['total']
                ])
        # Further export options for absent and overtime reports
        
        return response
    
    # PDF export would be similar to the previous report, using ReportLab

@login_required
@check_module_permission('reports', 'View')
def leave_analysis_report(request):
    """Generate leave analysis report"""
    if request.method == 'POST':
        form = LeaveReportForm(request.POST)
        if form.is_valid():
            # Get form data
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            department = form.cleaned_data['department']
            leave_type = form.cleaned_data['leave_type']
            status = form.cleaned_data['status']
            export_format = form.cleaned_data['export_format']
            
            # Build query
            query = Q(start_date__lte=end_date) & Q(end_date__gte=start_date)
            
            if department:
                query &= Q(employee__department=department)
            if leave_type:
                query &= Q(leave_type=leave_type)
            if status:
                query &= Q(status=status)
            
            # Get leave data
            leave_requests = LeaveRequest.objects.filter(query).select_related('employee', 'employee__department')
            
            # Handle export if requested
            if 'export' in request.POST:
                return export_leave_report(
                    leave_requests, export_format, start_date, end_date, department, leave_type, status
                )
            
            # Calculate statistics
            total_requests = leave_requests.count()
            total_days = leave_requests.aggregate(total=Sum('leave_days'))['total'] or 0
            
            # Leave by type
            leave_by_type = (
                leave_requests
                .values('leave_type')
                .annotate(
                    count=Count('request_id'),
                    days=Sum('leave_days')
                )
                .order_by('leave_type')
            )
            
            # Leave by status
            leave_by_status = (
                leave_requests
                .values('status')
                .annotate(count=Count('request_id'))
                .order_by('status')
            )
            
            # Leave by department
            leave_by_dept = (
                leave_requests
                .values('employee__department__department_name')
                .annotate(
                    count=Count('request_id'),
                    days=Sum('leave_days')
                )
                .order_by('employee__department__department_name')
            )
            
            # Top leave takers
            top_leave_takers = (
                leave_requests
                .values('employee__employee_id', 'employee__full_name', 'employee__department__department_name')
                .annotate(
                    count=Count('request_id'),
                    days=Sum('leave_days')
                )
                .order_by('-days')[:10]
            )
            
            context = {
                'form': form,
                'leave_requests': leave_requests,
                'start_date': start_date,
                'end_date': end_date,
                'department': department,
                'leave_type': leave_type,
                'status': status,
                'total_requests': total_requests,
                'total_days': total_days,
                'leave_by_type': leave_by_type,
                'leave_by_status': leave_by_status,
                'leave_by_dept': leave_by_dept,
                'top_leave_takers': top_leave_takers,
                'show_results': True
            }
            
            return render(request, 'reports/leave_analysis.html', context)
    else:
        # Initialize form with default dates (current year)
        today = date.today()
        start_date = date(today.year, 1, 1)
        end_date = date(today.year, 12, 31)
        
        form = LeaveReportForm(initial={
            'start_date': start_date,
            'end_date': end_date
        })
    
    return render(request, 'reports/leave_analysis.html', {'form': form})

def export_leave_report(leave_requests, export_format, start_date, end_date, department=None, leave_type=None, status=None):
    """Export leave report in requested format"""
    if export_format == 'excel':
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#3f51b5',
            'color': 'white',
            'border': 1
        })
        
        # Create summary worksheet
        summary_sheet = workbook.add_worksheet('Summary')
        
        # Add title
        title = f"Leave Analysis Report: {start_date} to {end_date}"
        if department:
            title += f" - {department.department_name} Department"
        if leave_type:
            title += f" - {leave_type}"
        if status:
            title += f" - {status} requests"
        
        summary_sheet.write(0, 0, title, workbook.add_format({'bold': True, 'font_size': 14}))
        summary_sheet.write(1, 0, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Add summary statistics
        summary_sheet.write(3, 0, "Summary Statistics", workbook.add_format({'bold': True}))
        
        total_requests = leave_requests.count()
        total_days = leave_requests.aggregate(total=Sum('leave_days'))['total'] or 0
        
        summary_sheet.write(4, 0, "Total Requests:")
        summary_sheet.write(4, 1, total_requests)
        
        summary_sheet.write(5, 0, "Total Leave Days:")
        summary_sheet.write(5, 1, float(total_days))
        
        # Leave by type
        leave_by_type = (
            leave_requests
            .values('leave_type')
            .annotate(
                count=Count('request_id'),
                days=Sum('leave_days')
            )
            .order_by('leave_type')
        )
        
        summary_sheet.write(7, 0, "Leave by Type", workbook.add_format({'bold': True}))
        summary_sheet.write(8, 0, "Leave Type", header_format)
        summary_sheet.write(8, 1, "Request Count", header_format)
        summary_sheet.write(8, 2, "Total Days", header_format)
        
        row = 9
        for leave in leave_by_type:
            summary_sheet.write(row, 0, leave['leave_type'])
            summary_sheet.write(row, 1, leave['count'])
            summary_sheet.write(row, 2, float(leave['days']))
            row += 1
        
        # Add chart
        chart = workbook.add_chart({'type': 'column'})
        chart.add_series({
            'name': 'Leave Requests',
            'categories': ['Summary', 9, 0, row-1, 0],
            'values': ['Summary', 9, 1, row-1, 1],
        })
        
        chart.set_title({'name': 'Leave Requests by Type'})
        chart.set_x_axis({'name': 'Leave Type'})
        chart.set_y_axis({'name': 'Count'})
        
        summary_sheet.insert_chart('E4', chart)
        
        # Leave by status
        leave_by_status = (
            leave_requests
            .values('status')
            .annotate(count=Count('request_id'))
            .order_by('status')
        )
        
        status_row = row + 2
        summary_sheet.write(status_row, 0, "Leave by Status", workbook.add_format({'bold': True}))
        summary_sheet.write(status_row + 1, 0, "Status", header_format)
        summary_sheet.write(status_row + 1, 1, "Request Count", header_format)
        
        status_row += 2
        for status in leave_by_status:
            summary_sheet.write(status_row, 0, status['status'])
            summary_sheet.write(status_row, 1, status['count'])
            status_row += 1
        
        # Add pie chart for status
        pie_chart = workbook.add_chart({'type': 'pie'})
        pie_chart.add_series({
            'name': 'Leave Status',
            'categories': ['Summary', row+2+2, 0, status_row-1, 0],
            'values': ['Summary', row+2+2, 1, status_row-1, 1],
        })
        
        pie_chart.set_title({'name': 'Leave Requests by Status'})
        summary_sheet.insert_chart('E20', pie_chart)
        
        # Create details worksheet
        detail_sheet = workbook.add_worksheet('Leave Details')
        
        # Add headers
        detail_sheet.write(0, 0, 'Request ID', header_format)
        detail_sheet.write(0, 1, 'Employee', header_format)
        detail_sheet.write(0, 2, 'Department', header_format)
        detail_sheet.write(0, 3, 'Leave Type', header_format)
        detail_sheet.write(0, 4, 'Start Date', header_format)
        detail_sheet.write(0, 5, 'End Date', header_format)
        detail_sheet.write(0, 6, 'Days', header_format)
        detail_sheet.write(0, 7, 'Status', header_format)
        detail_sheet.write(0, 8, 'Reason', header_format)
        
        for i, leave in enumerate(leave_requests, 1):
            detail_sheet.write(i, 0, leave.request_id)
            detail_sheet.write(i, 1, leave.employee.full_name)
            detail_sheet.write(i, 2, leave.employee.department.department_name if leave.employee.department else 'N/A')
            detail_sheet.write(i, 3, leave.leave_type)
            detail_sheet.write(i, 4, leave.start_date.strftime('%Y-%m-%d'))
            detail_sheet.write(i, 5, leave.end_date.strftime('%Y-%m-%d'))
            detail_sheet.write(i, 6, float(leave.leave_days))
            detail_sheet.write(i, 7, leave.status)
            detail_sheet.write(i, 8, leave.reason or '')
        
        # Auto-adjust column widths
        detail_sheet.set_column(0, 0, 10)
        detail_sheet.set_column(1, 1, 25)
        detail_sheet.set_column(2, 2, 20)
        detail_sheet.set_column(3, 3, 15)
        detail_sheet.set_column(4, 5, 12)
        detail_sheet.set_column(6, 7, 10)
        detail_sheet.set_column(8, 8, 40)
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"leave_report_{start_date}_to_{end_date}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    elif export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="leave_report_{start_date}_to_{end_date}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Request ID', 'Employee', 'Department', 'Leave Type', 'Start Date', 'End Date', 'Days', 'Status', 'Reason'])
        
        for leave in leave_requests:
            writer.writerow([
                leave.request_id,
                leave.employee.full_name,
                leave.employee.department.department_name if leave.employee.department else 'N/A',
                leave.leave_type,
                leave.start_date.strftime('%Y-%m-%d'),
                leave.end_date.strftime('%Y-%m-%d'),
                float(leave.leave_days),
                leave.status,
                leave.reason or ''
            ])
        
        return response
    
    # PDF export would be similar to the previous report, using ReportLab

def export_salary_report(salaries, report_type, export_format, month, year, department=None):
    """Export salary report in the requested format"""
    # Get month name
    month_name = calendar.month_name[int(month)]
    
    if export_format == 'excel':
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#3f51b5',
            'color': 'white',
            'border': 1
        })
        
        currency_format = workbook.add_format({
            'num_format': '#,##0.00'
        })
        
        # Create the main worksheet
        worksheet = workbook.add_worksheet('Salary Report')
        
        # Add title
        title = f"Salary Report - {month_name} {year}"
        if department:
            title += f" - {department.department_name} Department"
        
        worksheet.write(0, 0, title, workbook.add_format({'bold': True, 'font_size': 14}))
        worksheet.write(1, 0, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Headers
        headers = ['ID', 'Name', 'Department', 'Position', 'Base Salary', 'Allowance', 
                  'Bonus', 'Deductions', 'Tax', 'Insurance', 'Net Salary']
        
        for col, header in enumerate(headers):
            worksheet.write(3, col, header, header_format)
        
        # Write data
        row = 4
        for salary in salaries:
            worksheet.write(row, 0, salary.employee.employee_id)
            worksheet.write(row, 1, salary.employee.full_name)
            worksheet.write(row, 2, salary.employee.department.department_name if salary.employee.department else 'N/A')
            worksheet.write(row, 3, salary.employee.position.position_name if salary.employee.position else 'N/A')
            worksheet.write(row, 4, float(salary.base_salary), currency_format)
            worksheet.write(row, 5, float(salary.allowance), currency_format)
            worksheet.write(row, 6, float(salary.bonus), currency_format)
            worksheet.write(row, 7, float(salary.deductions), currency_format)
            worksheet.write(row, 8, float(salary.income_tax), currency_format)
            
            # Sum of all insurance types
            total_insurance = float(salary.social_insurance) + float(salary.health_insurance) + float(salary.unemployment_insurance)
            worksheet.write(row, 9, total_insurance, currency_format)
            
            worksheet.write(row, 10, float(salary.net_salary), currency_format)
            row += 1
        
        # Add totals
        worksheet.write(row + 1, 0, 'TOTAL', workbook.add_format({'bold': True}))
        worksheet.write(row + 1, 4, f'=SUM(E5:E{row})', workbook.add_format({'bold': True, 'num_format': '#,##0.00'}))
        worksheet.write(row + 1, 5, f'=SUM(F5:F{row})', workbook.add_format({'bold': True, 'num_format': '#,##0.00'}))
        worksheet.write(row + 1, 6, f'=SUM(G5:G{row})', workbook.add_format({'bold': True, 'num_format': '#,##0.00'}))
        worksheet.write(row + 1, 7, f'=SUM(H5:H{row})', workbook.add_format({'bold': True, 'num_format': '#,##0.00'}))
        worksheet.write(row + 1, 8, f'=SUM(I5:I{row})', workbook.add_format({'bold': True, 'num_format': '#,##0.00'}))
        worksheet.write(row + 1, 9, f'=SUM(J5:J{row})', workbook.add_format({'bold': True, 'num_format': '#,##0.00'}))
        worksheet.write(row + 1, 10, f'=SUM(K5:K{row})', workbook.add_format({'bold': True, 'num_format': '#,##0.00'}))
        
        # Add a summary sheet
        if report_type in ['summary', 'bank_transfer']:
            summary_sheet = workbook.add_worksheet('Summary')
            
            summary_sheet.write(0, 0, f"Salary Summary - {month_name} {year}", workbook.add_format({'bold': True, 'font_size': 14}))
            
            # Department summary
            summary_sheet.write(2, 0, "Salary by Department", workbook.add_format({'bold': True}))
            summary_sheet.write(3, 0, "Department", header_format)
            summary_sheet.write(3, 1, "Employees", header_format)
            summary_sheet.write(3, 2, "Total Salary", header_format)
            summary_sheet.write(3, 3, "Average Salary", header_format)
            
            # Group data by department
            dept_salaries = {}
            for salary in salaries:
                dept_name = salary.employee.department.department_name if salary.employee.department else 'No Department'
                
                if dept_name not in dept_salaries:
                    dept_salaries[dept_name] = {
                        'count': 0,
                        'total': 0,
                    }
                
                dept_salaries[dept_name]['count'] += 1
                dept_salaries[dept_name]['total'] += float(salary.net_salary)
            
            dept_row = 4
            for dept_name, data in dept_salaries.items():
                summary_sheet.write(dept_row, 0, dept_name)
                summary_sheet.write(dept_row, 1, data['count'])
                summary_sheet.write(dept_row, 2, data['total'], currency_format)
                summary_sheet.write(dept_row, 3, data['total'] / data['count'], currency_format)
                dept_row += 1
            
            # Add chart
            chart = workbook.add_chart({'type': 'column'})
            chart.add_series({
                'name': 'Total Salary',
                'categories': ['Summary', 4, 0, dept_row-1, 0],
                'values': ['Summary', 4, 2, dept_row-1, 2],
            })
            
            chart.set_title({'name': 'Total Salary by Department'})
            chart.set_x_axis({'name': 'Department'})
            chart.set_y_axis({'name': 'Amount'})
            
            summary_sheet.insert_chart('E3', chart, {'x_scale': 1.5, 'y_scale': 1.5})
        
        # Add a bank transfer list if that report type is selected
        if report_type == 'bank_transfer':
            transfer_sheet = workbook.add_worksheet('Bank Transfers')
            
            transfer_sheet.write(0, 0, f"Salary Bank Transfer List - {month_name} {year}", workbook.add_format({'bold': True, 'font_size': 14}))
            
            transfer_sheet.write(2, 0, "Employee ID", header_format)
            transfer_sheet.write(2, 1, "Employee Name", header_format)
            transfer_sheet.write(2, 2, "Bank Name", header_format)
            transfer_sheet.write(2, 3, "Account Number", header_format)
            transfer_sheet.write(2, 4, "Amount", header_format)
            transfer_sheet.write(2, 5, "Reference", header_format)
            
            transfer_row = 3
            for salary in salaries:
                # Note: In a real system, you would likely have bank details stored somewhere
                # This is a simplified example
                transfer_sheet.write(transfer_row, 0, salary.employee.employee_id)
                transfer_sheet.write(transfer_row, 1, salary.employee.full_name)
                transfer_sheet.write(transfer_row, 2, "Example Bank")  # Placeholder
                transfer_sheet.write(transfer_row, 3, f"ACCT{salary.employee.employee_id}")  # Placeholder
                transfer_sheet.write(transfer_row, 4, float(salary.net_salary), currency_format)
                transfer_sheet.write(transfer_row, 5, f"SALARY-{month}-{year}")
                transfer_row += 1
        
        # Add tax report if selected
        if report_type == 'tax':
            tax_sheet = workbook.add_worksheet('Tax Report')
            
            tax_sheet.write(0, 0, f"Income Tax Report - {month_name} {year}", workbook.add_format({'bold': True, 'font_size': 14}))
            
            tax_sheet.write(2, 0, "Employee ID", header_format)
            tax_sheet.write(2, 1, "Employee Name", header_format)
            tax_sheet.write(2, 2, "Tax Code", header_format)  # Would need to be fetched from employee profile
            tax_sheet.write(2, 3, "Taxable Income", header_format)
            tax_sheet.write(2, 4, "Tax Amount", header_format)
            tax_sheet.write(2, 5, "After Tax Income", header_format)
            
            tax_row = 3
            for salary in salaries:
                taxable_income = float(salary.base_salary) + float(salary.allowance) + float(salary.bonus)
                
                tax_sheet.write(tax_row, 0, salary.employee.employee_id)
                tax_sheet.write(tax_row, 1, salary.employee.full_name)
                tax_sheet.write(tax_row, 2, f"TX{salary.employee.employee_id}")  # Placeholder
                tax_sheet.write(tax_row, 3, taxable_income, currency_format)
                tax_sheet.write(tax_row, 4, float(salary.income_tax), currency_format)
                tax_sheet.write(tax_row, 5, taxable_income - float(salary.income_tax), currency_format)
                tax_row += 1
        
        # Auto-adjust column widths
        for sheet in workbook.worksheets():
            for col in range(20):  # Adjust up to 20 columns
                sheet.set_column(col, col, 15)
        
        workbook.close()
        output.seek(0)
        
        # Create response
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="salary_report_{month}_{year}.xlsx"'
        return response
    
    elif export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="salary_report_{month}_{year}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Name', 'Department', 'Position', 'Base Salary', 'Allowance', 
                        'Bonus', 'Deductions', 'Tax', 'Social Insurance', 'Health Insurance', 
                        'Unemployment Insurance', 'Net Salary'])
        
        for salary in salaries:
            writer.writerow([
                salary.employee.employee_id,
                salary.employee.full_name,
                salary.employee.department.department_name if salary.employee.department else 'N/A',
                salary.employee.position.position_name if salary.employee.position else 'N/A',
                float(salary.base_salary),
                float(salary.allowance),
                float(salary.bonus),
                float(salary.deductions),
                float(salary.income_tax),
                float(salary.social_insurance),
                float(salary.health_insurance),
                float(salary.unemployment_insurance),
                float(salary.net_salary)
            ])
        
        return response
    
    elif export_format == 'pdf':
        # Create a PDF using ReportLab
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="salary_report_{month}_{year}.pdf"'
        
        # Create the PDF object using ReportLab
        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        styles = getSampleStyleSheet()
        elements = []
        
        # Add title
        title = f"Salary Report - {month_name} {year}"
        if department:
            title += f" - {department.department_name} Department"
        
        elements.append(Paragraph(title, styles['Title']))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        # Create table data
        data = [['ID', 'Name', 'Department', 'Position', 'Base Salary', 'Allowance', 'Net Salary']]
        
        for salary in salaries:
            data.append([
                salary.employee.employee_id,
                salary.employee.full_name,
                salary.employee.department.department_name if salary.employee.department else 'N/A',
                salary.employee.position.position_name if salary.employee.position else 'N/A',
                f"{float(salary.base_salary):,.2f}",
                f"{float(salary.allowance):,.2f}",
                f"{float(salary.net_salary):,.2f}"
            ])
        
        # Calculate totals
        total_base = sum(float(s.base_salary) for s in salaries)
        total_allowance = sum(float(s.allowance) for s in salaries)
        total_net = sum(float(s.net_salary) for s in salaries)
        
        data.append([
            '', 'TOTAL', '', '', 
            f"{total_base:,.2f}", 
            f"{total_allowance:,.2f}", 
            f"{total_net:,.2f}"
        ])
        
        # Create the table
        table = Table(data)
        
        # Style the table
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT')
        ])
        
        table.setStyle(style)
        elements.append(table)
        
        # Build the PDF
        doc.build(elements)
        
        return response



@login_required
@check_module_permission('reports', 'View')
def salary_report(request):
    """Generate salary report"""
    if request.method == 'POST':
        form = PayrollReportForm(request.POST)
        if form.is_valid():
            # Get form data
            month = form.cleaned_data['month']
            year = form.cleaned_data['year']
            department = form.cleaned_data['department']
            report_type = form.cleaned_data['report_type']
            export_format = form.cleaned_data['export_format']
            
            # Build query
            query = Q(month=month, year=year)
            if department:
                query &= Q(employee__department=department)
            
            # Get salary data
            salaries = Salary.objects.filter(query).select_related('employee', 'employee__department', 'employee__position')
            
            if not salaries.exists():
                messages.warning(request, f'No salary data found for {month}/{year}')
                return redirect('salary_report')
            
            # Handle export if requested
            if 'export' in request.POST:
                return export_salary_report(
                    salaries, report_type, export_format, month, year, department
                )
            
            # Calculate statistics
            summary = {
                'total_salary': salaries.aggregate(total=Sum('net_salary'))['total'] or 0,
                'avg_salary': salaries.aggregate(avg=Avg('net_salary'))['avg'] or 0,
                'min_salary': salaries.aggregate(min=Min('net_salary'))['min'] or 0,
                'max_salary': salaries.aggregate(max=Max('net_salary'))['max'] or 0,
                'total_employees': salaries.count(),
                'total_tax': salaries.aggregate(total=Sum('income_tax'))['total'] or 0,
                'total_insurance': (
                    salaries.aggregate(total=Sum('social_insurance') + Sum('health_insurance') + Sum('unemployment_insurance'))['total'] or 0
                ),
                'total_deductions': salaries.aggregate(total=Sum('deductions'))['total'] or 0,
                'total_bonus': salaries.aggregate(total=Sum('bonus'))['total'] or 0
            }
            
            # Salary by department
            dept_salaries = (
                salaries
                .values('employee__department__department_name')
                .annotate(
                    count=Count('salary_id'),
                    total=Sum('net_salary'),
                    avg=Avg('net_salary')
                )
                .order_by('employee__department__department_name')
            )
            
            # Salary by position
            position_salaries = (
                salaries
                .values('employee__position__position_name')
                .annotate(
                    count=Count('salary_id'),
                    total=Sum('net_salary'),
                    avg=Avg('net_salary')
                )
                .order_by('employee__position__position_name')
            )
            
            context = {
                'form': form,
                'salaries': salaries,
                'month': month,
                'year': year,
                'department': department,
                'report_type': report_type,
                'summary': summary,
                'dept_salaries': dept_salaries,
                'position_salaries': position_salaries,
                'show_results': True
            }
            
            return render(request, 'reports/salary_report.html', context)
    else:
        # Initialize form with current month/year
        today = date.today()
        
        form = PayrollReportForm(initial={
            'month': today.month,
            'year': today.year
        })
    
    return render(request, 'reports/salary_report.html', {'form': form})

# Add more report views for performance, expense, and asset reports
@login_required
@check_module_permission('reports', 'View')
def payroll_summary_report(request):
    """Tạo báo cáo tổng hợp lương theo kỳ lương"""
    # Lấy năm và tháng hiện tại
    today = date.today()
    year = request.GET.get('year', today.year)
    
    try:
        year = int(year)
    except ValueError:
        year = today.year
    
    # Lấy dữ liệu lương theo tháng cho năm được chọn
    monthly_salary_data = []
    
    for month in range(1, 13):
        # Bỏ qua các tháng trong tương lai
        if year == today.year and month > today.month:
            continue
        
        # Lấy dữ liệu lương cho tháng này
        month_data = Salary.objects.filter(year=year, month=month)
        
        if month_data.exists():
            # Tính tổng lương và số lượng nhân viên
            total_gross = month_data.aggregate(total=Sum('base_salary') + Sum('allowance') + Sum('bonus'))['total'] or 0
            total_deductions = month_data.aggregate(total=Sum('deductions') + Sum('income_tax') + 
                                                   Sum('social_insurance') + Sum('health_insurance') + 
                                                   Sum('unemployment_insurance'))['total'] or 0
            total_net = month_data.aggregate(total=Sum('net_salary'))['total'] or 0
            employee_count = month_data.count()
            
            # Tính lương trung bình
            avg_salary = total_net / employee_count if employee_count > 0 else 0
            
            monthly_salary_data.append({
                'month': month,
                'month_name': calendar.month_name[month],
                'employee_count': employee_count,
                'total_gross': total_gross,
                'total_deductions': total_deductions,
                'total_net': total_net,
                'avg_salary': avg_salary
            })
    
    # Tính tổng chi phí lương cho năm
    yearly_data = Salary.objects.filter(year=year)
    yearly_total = yearly_data.aggregate(total=Sum('net_salary'))['total'] or 0
    yearly_employee_count = Employee.objects.filter(status='Working').count()
    
    # Lấy dữ liệu phân bổ lương theo phòng ban
    dept_salary_data = (
        Salary.objects.filter(year=year)
        .values('employee__department__department_name')
        .annotate(
            total=Sum('net_salary'),
            count=Count('salary_id', distinct=True)
        )
        .order_by('-total')
    )
    
    # Lấy các năm có dữ liệu lương
    available_years = Salary.objects.values_list('year', flat=True).distinct().order_by('-year')
    
    context = {
        'monthly_salary_data': monthly_salary_data,
        'yearly_total': yearly_total,
        'yearly_employee_count': yearly_employee_count,
        'dept_salary_data': dept_salary_data,
        'selected_year': year,
        'available_years': available_years,
        'title': f'Báo cáo tổng hợp lương năm {year}'
    }
    
    return render(request, 'reports/payroll_summary.html', context)

@login_required
@check_module_permission('reports', 'View')
def performance_analysis_report(request):
    """Tạo báo cáo phân tích hiệu suất nhân viên"""
    # Lấy tham số từ request
    department_id = request.GET.get('department', '')
    year = request.GET.get('year', date.today().year)
    quarter = request.GET.get('quarter', '')
    
    try:
        year = int(year)
    except ValueError:
        year = date.today().year
    
    # Xây dựng query
    query = Q(evaluation_year=year)
    
    if quarter:
        query &= Q(evaluation_quarter=quarter)
    
    if department_id:
        query &= Q(employee__department_id=department_id)
    
    # Lấy dữ liệu đánh giá hiệu suất
    evaluations = EmployeeEvaluation.objects.filter(query).select_related('employee', 'employee__department')
    
    if not evaluations.exists():
        messages.warning(request, f'Không tìm thấy dữ liệu đánh giá hiệu suất cho các tham số đã chọn')
    
    # Tính điểm trung bình theo phòng ban
    dept_performance = (
        evaluations
        .values('employee__department__department_name')
        .annotate(
            avg_score=Avg('overall_score'),
            count=Count('evaluation_id')
        )
        .order_by('-avg_score')
    )
    
    # Tính điểm trung bình theo quý (nếu có dữ liệu cho nhiều quý)
    quarter_performance = None
    if not quarter:
        quarter_performance = (
            evaluations
            .values('evaluation_quarter')
            .annotate(
                avg_score=Avg('overall_score'),
                count=Count('evaluation_id')
            )
            .order_by('evaluation_quarter')
        )
    
    # Lấy top 10 nhân viên có hiệu suất cao nhất
    top_performers = evaluations.order_by('-overall_score')[:10]
    
    # Lấy top 10 nhân viên cần cải thiện
    improvement_needed = evaluations.order_by('overall_score')[:10]
    
    # Lấy danh sách phòng ban cho bộ lọc
    departments = Department.objects.filter(status=1)
    
    # Lấy các năm có dữ liệu đánh giá
    available_years = EmployeeEvaluation.objects.values_list(
        'evaluation_year', flat=True
    ).distinct().order_by('-evaluation_year')
    
    context = {
        'evaluations': evaluations,
        'dept_performance': dept_performance,
        'quarter_performance': quarter_performance,
        'top_performers': top_performers,
        'improvement_needed': improvement_needed,
        'departments': departments,
        'selected_department': department_id,
        'selected_year': year,
        'selected_quarter': quarter,
        'available_years': available_years,
        'title': 'Báo cáo phân tích hiệu suất'
    }
    
    # Kiểm tra nếu yêu cầu xuất dữ liệu
    if 'export' in request.GET:
        export_format = request.GET.get('format', 'excel')
        return export_report('performance', export_format, context)
    
    return render(request, 'reports/performance_analysis.html', context)

@login_required
@check_module_permission('reports', 'View')
def kpi_summary_report(request):
    """Tạo báo cáo tổng hợp KPI"""
    # Lấy tham số từ request
    department_id = request.GET.get('department', '')
    year = request.GET.get('year', date.today().year)
    quarter = request.GET.get('quarter', '')
    
    try:
        year = int(year)
    except ValueError:
        year = date.today().year
    
    # Xây dựng query
    query = Q(year=year)
    
    if quarter:
        query &= Q(quarter=quarter)
    
    if department_id:
        query &= Q(department_id=department_id)
    
    # Lấy dữ liệu KPI
    kpis = KPI.objects.filter(query).select_related('department', 'employee')
    
    if not kpis.exists():
        messages.warning(request, f'Không tìm thấy dữ liệu KPI cho các tham số đã chọn')
    
    # Tính tỷ lệ hoàn thành KPI theo phòng ban
    dept_kpi_completion = (
        kpis
        .values('department__department_name')
        .annotate(
            avg_completion=Avg(
                Case(
                    When(target_value__gt=0, then=F('actual_value') * 100 / F('target_value')),
                    default=0,
                    output_field=models.FloatField()
                )
            ),
            count=Count('kpi_id')
        )
        .order_by('-avg_completion')
    )
    
    # Tính tỷ lệ hoàn thành KPI theo quý (nếu không chọn quý cụ thể)
    quarter_kpi_completion = None
    if not quarter:
        quarter_kpi_completion = (
            kpis
            .values('quarter')
            .annotate(
                avg_completion=Avg(
                    Case(
                        When(target_value__gt=0, then=F('actual_value') * 100 / F('target_value')),
                        default=0,
                        output_field=models.FloatField()
                    )
                ),
                count=Count('kpi_id')
            )
            .order_by('quarter')
        )
    
    # Lấy KPI có tỷ lệ hoàn thành cao nhất
    top_kpis = (
        kpis
        .annotate(
            completion_rate=Case(
                When(target_value__gt=0, then=F('actual_value') * 100 / F('target_value')),
                default=0,
                output_field=models.FloatField()
            )
        )
        .order_by('-completion_rate')[:10]
    )
    
    # Lấy KPI có tỷ lệ hoàn thành thấp nhất
    low_kpis = (
        kpis
        .annotate(
            completion_rate=Case(
                When(target_value__gt=0, then=F('actual_value') * 100 / F('target_value')),
                default=0,
                output_field=models.FloatField()
            )
        )
        .filter(target_value__gt=0)
        .order_by('completion_rate')[:10]
    )
    
    # Lấy danh sách phòng ban cho bộ lọc
    departments = Department.objects.filter(status=1)
    
    # Lấy các năm có dữ liệu KPI
    available_years = KPI.objects.values_list('year', flat=True).distinct().order_by('-year')
    
    context = {
        'kpis': kpis,
        'dept_kpi_completion': dept_kpi_completion,
        'quarter_kpi_completion': quarter_kpi_completion,
        'top_kpis': top_kpis,
        'low_kpis': low_kpis,
        'departments': departments,
        'selected_department': department_id,
        'selected_year': year,
        'selected_quarter': quarter,
        'available_years': available_years,
        'title': 'Báo cáo tổng hợp KPI'
    }
    
    # Kiểm tra nếu yêu cầu xuất dữ liệu
    if 'export' in request.GET:
        export_format = request.GET.get('format', 'excel')
        return export_report('kpi', export_format, context)
    
    return render(request, 'reports/kpi_summary.html', context)

@login_required
@check_module_permission('reports', 'View')
def asset_utilization_report(request):
    """Tạo báo cáo sử dụng tài sản"""
    # Lấy tham số từ request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category_id = request.GET.get('category', '')
    department_id = request.GET.get('department', '')
    
    # Nếu không có ngày bắt đầu và kết thúc, sử dụng năm hiện tại
    if not start_date or not end_date:
        today = date.today()
        start_date = date(today.year, 1, 1).strftime('%Y-%m-%d')
        end_date = date(today.year, 12, 31).strftime('%Y-%m-%d')
    
    # Xây dựng query
    asset_query = Q()
    if category_id:
        asset_query &= Q(category_id=category_id)
    
    # Lấy dữ liệu tài sản
    assets = Asset.objects.filter(asset_query)
    
    # Lấy dữ liệu gán tài sản
    assignment_query = Q(assignment_date__gte=start_date, assignment_date__lte=end_date)
    if department_id:
        assignment_query &= Q(employee__department_id=department_id)
    
    assignments = AssetAssignment.objects.filter(assignment_query).select_related('asset', 'employee')
    
    # Tính tỷ lệ sử dụng tài sản
    total_assets = assets.count()
    assigned_assets = assets.filter(status='Assigned').count()
    utilization_rate = (assigned_assets / total_assets * 100) if total_assets > 0 else 0
    
    # Phân tích theo danh mục
    category_stats = (
        assets
        .values('category__name')
        .annotate(
            total=Count('asset_id'),
            assigned=Count('asset_id', filter=Q(status='Assigned')),
            available=Count('asset_id', filter=Q(status='Available')),
            maintenance=Count('asset_id', filter=Q(status='Under Maintenance')),
            retired=Count('asset_id', filter=Q(status='Retired'))
        )
        .order_by('category__name')
    )
    
    # Tính tỷ lệ sử dụng cho mỗi danh mục
    for stat in category_stats:
        stat['utilization_rate'] = (stat['assigned'] / stat['total'] * 100) if stat['total'] > 0 else 0
    
    # Phân tích theo phòng ban
    dept_stats = (
        assignments
        .values('employee__department__department_name')
        .annotate(
            count=Count('assignment_id'),
            distinct_assets=Count('asset', distinct=True)
        )
        .order_by('-count')
    )
    
    # Lấy top 10 nhân viên sử dụng nhiều tài sản nhất
    top_users = (
        assignments
        .values('employee__employee_id', 'employee__full_name', 'employee__department__department_name')
        .annotate(count=Count('assignment_id'))
        .order_by('-count')[:10]
    )
    
    # Lấy danh sách danh mục tài sản và phòng ban cho bộ lọc
    categories = AssetCategory.objects.all()
    departments = Department.objects.filter(status=1)
    
    context = {
        'assets': assets,
        'assignments': assignments,
        'total_assets': total_assets,
        'assigned_assets': assigned_assets,
        'utilization_rate': round(utilization_rate, 2),
        'category_stats': category_stats,
        'dept_stats': dept_stats,
        'top_users': top_users,
        'categories': categories,
        'departments': departments,
        'start_date': start_date,
        'end_date': end_date,
        'selected_category': category_id,
        'selected_department': department_id,
        'title': 'Báo cáo sử dụng tài sản'
    }
    
    # Kiểm tra nếu yêu cầu xuất dữ liệu
    if 'export' in request.GET:
        export_format = request.GET.get('format', 'excel')
        return export_report('asset', export_format, context)
    
    return render(request, 'reports/asset_utilization.html', context)

@login_required
@check_module_permission('reports', 'View')
def expense_analysis_report(request):
    """Tạo báo cáo phân tích chi phí"""
    # Lấy tham số từ request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category_id = request.GET.get('category', '')
    department_id = request.GET.get('department', '')
    
    # Nếu không có ngày bắt đầu và kết thúc, sử dụng năm hiện tại
    if not start_date or not end_date:
        today = date.today()
        start_date = date(today.year, 1, 1).strftime('%Y-%m-%d')
        end_date = date(today.year, 12, 31).strftime('%Y-%m-%d')
    
    # Xây dựng query
    query = Q(submission_date__gte=start_date, submission_date__lte=end_date, status__in=['Approved', 'Paid'])
    
    if department_id:
        query &= Q(employee__department_id=department_id)
    
    # Lấy dữ liệu chi phí
    expenses = ExpenseClaim.objects.filter(query).select_related('employee', 'employee__department')
    
    # Lọc theo danh mục nếu có
    expense_items = ExpenseItem.objects.filter(expense_claim__in=expenses)
    if category_id:
        expense_items = expense_items.filter(category_id=category_id)
    
    # Tính tổng chi phí
    total_amount = expenses.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Phân tích theo danh mục
    category_expenses = (
        expense_items
        .values('category__name')
        .annotate(
            total=Sum('amount'),
            count=Count('item_id')
        )
        .order_by('-total')
    )
    
    # Phân tích theo phòng ban
    dept_expenses = (
        expenses
        .values('employee__department__department_name')
        .annotate(
            total=Sum('total_amount'),
            count=Count('claim_id')
        )
        .order_by('-total')
    )
    
    # Phân tích theo nhân viên
    employee_expenses = (
        expenses
        .values('employee__employee_id', 'employee__full_name', 'employee__department__department_name')
        .annotate(
            total=Sum('total_amount'),
            count=Count('claim_id')
        )
        .order_by('-total')[:10]
    )
    
    # Phân tích theo tháng
    month_expenses = (
        expenses
        .annotate(month=TruncMonth('submission_date'))
        .values('month')
        .annotate(
            total=Sum('total_amount'),
            count=Count('claim_id')
        )
        .order_by('month')
    )
    
    # Tính chi phí trung bình
    avg_expense = total_amount / expenses.count() if expenses.count() > 0 else 0
    
    # Lấy danh sách danh mục và phòng ban cho bộ lọc
    categories = ExpenseCategory.objects.filter(is_active=True)
    departments = Department.objects.filter(status=1)
    
    context = {
        'expenses': expenses,
        'total_amount': total_amount,
        'avg_expense': avg_expense,
        'category_expenses': category_expenses,
        'dept_expenses': dept_expenses,
        'employee_expenses': employee_expenses,
        'month_expenses': month_expenses,
        'categories': categories,
        'departments': departments,
        'start_date': start_date,
        'end_date': end_date,
        'selected_category': category_id,
        'selected_department': department_id,
        'title': 'Báo cáo phân tích chi phí'
    }
    
    # Kiểm tra nếu yêu cầu xuất dữ liệu
    if 'export' in request.GET:
        export_format = request.GET.get('format', 'excel')
        return export_report('expense', export_format, context)
    
    return render(request, 'reports/expense_analysis.html', context)

@login_required
@check_module_permission('reports', 'View')
def report_comparison(request):
    """Tạo báo cáo so sánh giữa các kỳ"""
    # Lấy tham số từ request
    report_type = request.GET.get('type', 'headcount')
    period1 = request.GET.get('period1', '')
    period2 = request.GET.get('period2', '')
    
    # Lấy danh sách các loại báo cáo có thể so sánh
    report_types = [
        {'id': 'headcount', 'name': 'Số lượng nhân viên'},
        {'id': 'turnover', 'name': 'Tỷ lệ nghỉ việc'},
        {'id': 'salary', 'name': 'Lương bình quân'},
        {'id': 'performance', 'name': 'Hiệu suất'},
        {'id': 'attendance', 'name': 'Tỷ lệ đi làm'},
        {'id': 'leave', 'name': 'Nghỉ phép'},
    ]
    
    # Lấy danh sách các kỳ có thể so sánh
    periods = []
    current_year = date.today().year
    
    # Thêm các quý trong 2 năm gần nhất
    for year in range(current_year-1, current_year+1):
        for quarter in range(1, 5):
            # Bỏ qua các quý trong tương lai
            if year == current_year and quarter > ((date.today().month-1) // 3 + 1):
                continue
            periods.append({
                'id': f'Q{quarter}-{year}',
                'name': f'Quý {quarter}/{year}'
            })
    
    # Thêm các tháng trong năm hiện tại
    for month in range(1, 13):
        # Bỏ qua các tháng trong tương lai
        if month > date.today().month:
            continue
        periods.append({
            'id': f'M{month}-{current_year}',
            'name': f'Tháng {month}/{current_year}'
        })
    
    # Sắp xếp các kỳ theo thứ tự thời gian
    periods.sort(key=lambda x: x['id'])
    
    context = {
        'report_types': report_types,
        'periods': periods,
        'selected_type': report_type,
        'selected_period1': period1,
        'selected_period2': period2,
        'title': 'So sánh báo cáo'
    }
    
    return render(request, 'reports/report_comparison.html', context)

@login_required
@check_module_permission('reports', 'View')
def comparison_data(request):
    """API trả về dữ liệu so sánh cho biểu đồ"""
    report_type = request.GET.get('type', 'headcount')
    period1 = request.GET.get('period1', '')
    period2 = request.GET.get('period2', '')
    
    # Kiểm tra tham số
    if not period1 or not period2:
        return JsonResponse({'error': 'Thiếu tham số kỳ so sánh'}, status=400)
    
    # Phân tích kỳ thành tháng/quý và năm
    period1_type = period1[0]  # 'Q' hoặc 'M'
    period1_value = int(period1[1:].split('-')[0])
    period1_year = int(period1.split('-')[1])
    
    period2_type = period2[0]
    period2_value = int(period2[1:].split('-')[0])
    period2_year = int(period2.split('-')[1])
    
    # Lấy dữ liệu theo loại báo cáo
    if report_type == 'headcount':
        # Lấy dữ liệu số lượng nhân viên theo phòng ban
        data = get_headcount_comparison_data(
            period1_type, period1_value, period1_year,
            period2_type, period2_value, period2_year
        )
   
    else:
        return JsonResponse({'error': 'Loại báo cáo không hợp lệ'}, status=400)
    
    return JsonResponse(data)

@login_required
@check_module_permission('reports', 'View')
def export_report(request, report_type):
    """Xuất báo cáo theo định dạng"""
    export_format = request.GET.get('format', 'excel')
    
    # Lấy tham số theo loại báo cáo
    if report_type == 'employee':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        department_id = request.GET.get('department')
        position_id = request.GET.get('position')
        status = request.GET.get('status')
        
        # Xây dựng query
        query = Q()
        if department_id:
            query &= Q(department_id=department_id)
        if position_id:
            query &= Q(position_id=position_id)
        if status:
            query &= Q(status=status)
        
        # Lấy dữ liệu nhân viên
        employees = Employee.objects.filter(query).select_related('department', 'position')
        
        # Gọi hàm xuất báo cáo nhân viên
        return export_employee_report(employees, 'detailed', export_format, start_date, end_date)
    
    elif report_type == 'attendance':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        department_id = request.GET.get('department')
        
        # Xây dựng query cho nhân viên
        employee_query = Q(status='Working')
        if department_id:
            employee_query &= Q(department_id=department_id)
        
        employees = Employee.objects.filter(employee_query)
        
        # Xây dựng query cho dữ liệu chấm công
        attendance_query = Q(work_date__gte=start_date, work_date__lte=end_date)
        attendances = Attendance.objects.filter(attendance_query)
        
        # Gọi hàm xuất báo cáo chấm công
        return export_attendance_report(attendances, employees, 'detailed', export_format, start_date, end_date)
    
    elif report_type == 'leave':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        department_id = request.GET.get('department')
        leave_type = request.GET.get('leave_type')
        status = request.GET.get('status')
        
        # Xây dựng query
        query = Q(start_date__lte=end_date) & Q(end_date__gte=start_date)
        
        if department_id:
            query &= Q(employee__department_id=department_id)
        if leave_type:
            query &= Q(leave_type=leave_type)
        if status:
            query &= Q(status=status)
        
        # Lấy dữ liệu nghỉ phép
        leave_requests = LeaveRequest.objects.filter(query).select_related('employee', 'employee__department')
        
        # Gọi hàm xuất báo cáo nghỉ phép
        return export_leave_report(leave_requests, export_format, start_date, end_date)
    
    elif report_type == 'salary':
        month = request.GET.get('month')
        year = request.GET.get('year')
        department_id = request.GET.get('department')
        
        # Xây dựng query
        query = Q(month=month, year=year)
        if department_id:
            query &= Q(employee__department_id=department_id)
        
        # Lấy dữ liệu lương
        salaries = Salary.objects.filter(query).select_related('employee', 'employee__department', 'employee__position')
        
        # Gọi hàm xuất báo cáo lương
        return export_salary_report(salaries, 'detailed', export_format, month, year)
    
    # Các loại báo cáo khác...
    
    return redirect('hr_reports')

@login_required
@check_module_permission('reports', 'View')
def saved_report_list(request):
    """Hiển thị danh sách báo cáo đã lưu"""
    reports = HRReport.objects.all().order_by('-created_date')
    
    # Lọc theo loại báo cáo nếu có
    report_type = request.GET.get('type')
    if report_type:
        reports = reports.filter(report_type=report_type)
    
    # Phân trang
    paginator = Paginator(reports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Lấy danh sách các loại báo cáo
    report_types = HRReport.REPORT_TYPE_CHOICES
    
    return render(request, 'reports/saved_report_list.html', {
        'page_obj': page_obj,
        'report_types': report_types,
        'selected_type': report_type,
        'title': 'Báo cáo đã lưu'
    })

@login_required
@check_module_permission('reports', 'View')
def saved_report_detail(request, report_id):
    """Xem chi tiết báo cáo đã lưu"""
    report = get_object_or_404(HRReport, report_id=report_id)
    
    return render(request, 'reports/saved_report_detail.html', {
        'report': report,
        'title': f'Báo cáo: {report.title}'
    })

@login_required
@check_module_permission('reports', 'Edit')
def save_current_report(request):
    """Lưu báo cáo hiện tại"""
    if request.method == 'POST':
        # Lấy dữ liệu từ form
        report_type = request.POST.get('report_type')
        title = request.POST.get('title')
        content = request.POST.get('content')  # Có thể là HTML hoặc JSON
        report_period = request.POST.get('report_period')
        
        # Tạo báo cáo mới
        report = HRReport(
            report_type=report_type,
            title=title,
            content=content,
            report_period=report_period,
            created_by=request.user.employee if hasattr(request.user, 'employee') else None
        )
        
        # Lưu file báo cáo nếu có
        if 'report_file' in request.FILES:
            report.report_file = request.FILES['report_file']
        
        report.save()
        
        messages.success(request, 'Báo cáo đã được lưu thành công.')
        return redirect('saved_report_detail', report_id=report.report_id)
    
    # Nếu không phải POST, chuyển hướng về trang báo cáo
    return redirect('hr_reports')

# Các hàm hỗ trợ cho so sánh dữ liệu
def get_headcount_comparison_data(period1_type, period1_value, period1_year, period2_type, period2_value, period2_year):
    """Lấy dữ liệu so sánh số lượng nhân viên"""
    # Xác định ngày bắt đầu và kết thúc cho kỳ 1
    if period1_type == 'Q':
        # Quý
        start_month1 = (period1_value - 1) * 3 + 1
        end_month1 = start_month1 + 2
        start_date1 = date(period1_year, start_month1, 1)
        if end_month1 == 12:
            end_date1 = date(period1_year, end_month1, 31)
        else:
            end_date1 = date(period1_year, end_month1 + 1, 1) - timedelta(days=1)
    else:
        # Tháng
        start_date1 = date(period1_year, period1_value, 1)
        if period1_value == 12:
            end_date1 = date(period1_year, 12, 31)
        else:
            end_date1 = date(period1_year, period1_value + 1, 1) - timedelta(days=1)
    
    # Xác định ngày bắt đầu và kết thúc cho kỳ 2
    if period2_type == 'Q':
        # Quý
        start_month2 = (period2_value - 1) * 3 + 1
        end_month2 = start_month2 + 2
        start_date2 = date(period2_year, start_month2, 1)
        if end_month2 == 12:
            end_date2 = date(period2_year, end_month2, 31)
        else:
            end_date2 = date(period2_year, end_month2 + 1, 1) - timedelta(days=1)
    else:
        # Tháng
        start_date2 = date(period2_year, period2_value, 1)
        if period2_value == 12:
            end_date2 = date(period2_year, 12, 31)
        else:
            end_date2 = date(period2_year, period2_value + 1, 1) - timedelta(days=1)
    
    # Lấy số lượng nhân viên theo phòng ban cho kỳ 1
    headcount1 = Employee.objects.filter(
        status='Working',
        hire_date__lte=end_date1
    ).exclude(
        status='Resigned',
        updated_date__lt=end_date1
    ).values('department__department_name').annotate(count=Count('employee_id'))
    
    # Lấy số lượng nhân viên theo phòng ban cho kỳ 2
    headcount2 = Employee.objects.filter(
        status='Working',
        hire_date__lte=end_date2
    ).exclude(
        status='Resigned',
        updated_date__lt=end_date2
    ).values('department__department_name').annotate(count=Count('employee_id'))
    
    # Chuyển đổi thành từ điển để dễ so sánh
    dept_headcount1 = {item['department__department_name'] or 'Không xác định': item['count'] for item in headcount1}
    dept_headcount2 = {item['department__department_name'] or 'Không xác định': item['count'] for item in headcount2}
    
    # Lấy danh sách tất cả các phòng ban
    all_departments = set(list(dept_headcount1.keys()) + list(dept_headcount2.keys()))
    
    # Tạo dữ liệu so sánh
    comparison_data = []
    for dept in all_departments:
        count1 = dept_headcount1.get(dept, 0)
        count2 = dept_headcount2.get(dept, 0)
        change = count2 - count1
        change_percent = (change / count1 * 100) if count1 > 0 else 0
        
        comparison_data.append({
            'department': dept,
            'period1_count': count1,
            'period2_count': count2,
            'change': change,
            'change_percent': round(change_percent, 2)
        })
    
    # Sắp xếp theo phòng ban
    comparison_data.sort(key=lambda x: x['department'])
    
    # Tính tổng số nhân viên
    total1 = sum(dept_headcount1.values())
    total2 = sum(dept_headcount2.values())
    total_change = total2 - total1
    total_change_percent = (total_change / total1 * 100) if total1 > 0 else 0
    
    # Tạo dữ liệu trả về
    result = {
        'period1': f"{'Quý' if period1_type == 'Q' else 'Tháng'} {period1_value}/{period1_year}",
        'period2': f"{'Quý' if period2_type == 'Q' else 'Tháng'} {period2_value}/{period2_year}",
        'departments': [item['department'] for item in comparison_data],
        'period1_data': [item['period1_count'] for item in comparison_data],
        'period2_data': [item['period2_count'] for item in comparison_data],
        'changes': [item['change'] for item in comparison_data],
        'change_percents': [item['change_percent'] for item in comparison_data],
        'total1': total1,
        'total2': total2,
        'total_change': total_change,
        'total_change_percent': round(total_change_percent, 2)
    }
    
    return result
