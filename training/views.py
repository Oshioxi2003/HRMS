from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils.translation import gettext as _
from django.db.models import Q, Count, Sum, Avg
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from datetime import date, datetime, timedelta
import csv
import xlsxwriter
from io import BytesIO
from .models import *
from .forms import *
from employee.models import *
from accounts.decorators import *
from notifications.services import create_notification
import calendar
import json




@login_required
@check_module_permission('training', 'View')
def course_list(request):
    """List all training courses"""
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    courses = TrainingCourse.objects.all().order_by('-start_date')
    
    if query:
        courses = courses.filter(
            Q(course_name__icontains=query) |
            Q(organizer__icontains=query) |
            Q(location__icontains=query)
        )
    
    if status_filter:
        courses = courses.filter(status=status_filter)
    
    # Add participant count to each course
    for course in courses:
        course.participant_count = TrainingParticipation.objects.filter(course=course).count()
    
    paginator = Paginator(courses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'training/course_list.html', {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter
    })

@login_required
@hr_required
def course_create(request):
    """Create a new training course"""
    if request.method == 'POST':
        form = TrainingCourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(request, 'Training course created successfully')
            return redirect('course_detail', pk=course.course_id)
    else:
        form = TrainingCourseForm()
    
    return render(request, 'training/course_form.html', {
        'form': form,
        'title': 'Create Training Course',
        'is_create': True
    })

@login_required
@check_module_permission('training', 'View')
def course_detail(request, pk):
    """View details of a training course"""
    course = get_object_or_404(TrainingCourse, pk=pk)
    
    # Get participants for this course
    participants = TrainingParticipation.objects.filter(course=course).select_related('employee')
    
    # Calculate statistics
    stats = {
        'total_participants': participants.count(),
        'completed': participants.filter(status='Completed').count(),
        'participating': participants.filter(status='Participating').count(),
        'registered': participants.filter(status='Registered').count(),
        'cancelled': participants.filter(status='Cancelled').count(),
        'avg_score': participants.filter(score__isnull=False).aggregate(Avg('score'))['score__avg'] or 0
    }
    
    # Check if current user is already registered
    if request.user.employee:
        user_is_registered = participants.filter(employee=request.user.employee).exists()
        if user_is_registered:
            user_participation = participants.get(employee=request.user.employee)
        else:
            user_participation = None
    else:
        user_is_registered = False
        user_participation = None
    
    # Check if course is open for registration
    can_register = course.status in ['Preparing', 'In Progress'] and not user_is_registered
    
    # Check if user has permission to edit/manage
    can_manage = request.user.role in ['HR', 'Admin']
    
    return render(request, 'training/course_detail.html', {
        'course': course,
        'participants': participants,
        'stats': stats,
        'user_is_registered': user_is_registered,
        'user_participation': user_participation,
        'can_register': can_register,
        'can_manage': can_manage
    })

@login_required
@hr_required
def course_update(request, pk):
    """Update a training course"""
    course = get_object_or_404(TrainingCourse, pk=pk)
    
    if request.method == 'POST':
        form = TrainingCourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Training course updated successfully')
            return redirect('course_detail', pk=pk)
    else:
        form = TrainingCourseForm(instance=course)
    
    return render(request, 'training/course_form.html', {
        'form': form,
        'title': 'Update Training Course',
        'course': course,
        'is_create': False
    })

@login_required
@hr_required
def course_delete(request, pk):
    """Delete a training course"""
    course = get_object_or_404(TrainingCourse, pk=pk)
    
    if request.method == 'POST':
        course_name = course.course_name
        course.delete()
        messages.success(request, f'Training course "{course_name}" has been deleted')
        return redirect('course_list')
    
    return render(request, 'training/course_delete.html', {'course': course})

@login_required
@check_module_permission('training', 'View')
def course_participants(request, course_id):
    """View and manage participants for a course"""
    course = get_object_or_404(TrainingCourse, pk=course_id)
    
    # Get participants with filter
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    participants = TrainingParticipation.objects.filter(course=course).select_related('employee')
    
    if status_filter:
        participants = participants.filter(status=status_filter)
    
    if search_query:
        participants = participants.filter(
            Q(employee__full_name__icontains=search_query) |
            Q(employee__email__icontains=search_query)
        )
    
    # Calculate statistics
    stats = {
        'total': participants.count(),
        'completed': participants.filter(status='Completed').count(),
        'participating': participants.filter(status='Participating').count(),
        'registered': participants.filter(status='Registered').count(),
        'cancelled': participants.filter(status='Cancelled').count()
    }
    
    # Check permissions
    can_manage = request.user.role in ['HR', 'Admin']
    
    return render(request, 'training/course_participants.html', {
        'course': course,
        'participants': participants,
        'stats': stats,
        'status_filter': status_filter,
        'search_query': search_query,
        'can_manage': can_manage
    })

@login_required
@hr_required
def add_participants(request, course_id):
    """Add participants to a course"""
    course = get_object_or_404(TrainingCourse, pk=course_id)
    
    if request.method == 'POST':
        selected_employees = request.POST.getlist('employees')
        
        if not selected_employees:
            messages.warning(request, 'No employees selected')
            return redirect('add_participants', course_id=course_id)
        
        added_count = 0
        already_count = 0
        
        for employee_id in selected_employees:
            try:
                employee = Employee.objects.get(pk=employee_id)
                
                # Check if already registered
                if TrainingParticipation.objects.filter(employee=employee, course=course).exists():
                    already_count += 1
                    continue
                
                # Create participation record
                participation = TrainingParticipation(
                    employee=employee,
                    course=course,
                    registration_date=date.today(),
                    status='Registered'
                )
                participation.save()
                added_count += 1
                
            except Employee.DoesNotExist:
                continue
        
        if added_count > 0:
            messages.success(request, f'Successfully added {added_count} participant(s) to the course')
        
        if already_count > 0:
            messages.info(request, f'{already_count} employee(s) were already registered for this course')
        
        return redirect('course_participants', course_id=course_id)
    
    # Get all employees who are not already registered
    existing_participants = TrainingParticipation.objects.filter(course=course).values_list('employee_id', flat=True)
    available_employees = Employee.objects.filter(status='Working').exclude(employee_id__in=existing_participants)
    
    # Apply search filter if provided
    search_query = request.GET.get('q', '')
    if search_query:
        available_employees = available_employees.filter(
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(department__department_name__icontains=search_query)
        )
    
    # Apply department filter if provided
    department_filter = request.GET.get('department', '')
    if department_filter:
        available_employees = available_employees.filter(department_id=department_filter)
    
    # Get departments for filter dropdown
    departments = Department.objects.filter(status=1)
    
    return render(request, 'training/add_participants.html', {
        'course': course,
        'available_employees': available_employees,
        'search_query': search_query,
        'department_filter': department_filter,
        'departments': departments
    })

@login_required
@check_module_permission('training', 'Edit')
def update_participation_status(request, participation_id):
    """Update participation status and evaluate training completion"""
    participation = get_object_or_404(TrainingParticipation, pk=participation_id)
    
    if request.method == 'POST':
        form = TrainingEvaluationForm(request.POST, instance=participation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Participation status updated successfully')
            return redirect('course_participants', course_id=participation.course.course_id)
    else:
        form = TrainingEvaluationForm(instance=participation)
    
    return render(request, 'training/participation_form.html', {
        'form': form,
        'participation': participation,
        'course': participation.course,
        'employee': participation.employee
    })

@login_required
@hr_required
def delete_participation(request, participation_id):
    """Delete a participant from a course"""
    participation = get_object_or_404(TrainingParticipation, pk=participation_id)
    course_id = participation.course.course_id
    
    if request.method == 'POST':
        employee_name = participation.employee.full_name
        participation.delete()
        messages.success(request, f'Removed {employee_name} from the course')
        return redirect('course_participants', course_id=course_id)
    
    return render(request, 'training/delete_participation.html', {
        'participation': participation,
        'course': participation.course
    })

@login_required
def register_for_course(request, course_id):
    """Register for a training course (for employees)"""
    course = get_object_or_404(TrainingCourse, pk=course_id)
    
    # Check if employee profile exists
    if not request.user.employee:
        messages.error(request, 'You do not have an employee profile')
        return redirect('course_detail', pk=course_id)
    
    # Check if course is open for registration
    if course.status not in ['Preparing', 'In Progress']:
        messages.error(request, 'Registration is not open for this course')
        return redirect('course_detail', pk=course_id)
    
    # Check if already registered
    if TrainingParticipation.objects.filter(employee=request.user.employee, course=course).exists():
        messages.warning(request, 'You are already registered for this course')
        return redirect('course_detail', pk=course_id)
    
    if request.method == 'POST':
        form = TrainingRegistrationForm(request.POST, course=course, employee=request.user.employee)
        if form.is_valid():
            form.save()
            messages.success(request, 'You have successfully registered for this course')
            return redirect('my_training')
    else:
        form = TrainingRegistrationForm(course=course, employee=request.user.employee)
    
    return render(request, 'training/register_course.html', {
        'form': form,
        'course': course
    })

@login_required
def cancel_registration(request, participation_id):
    """Cancel registration for a course"""
    participation = get_object_or_404(
        TrainingParticipation, 
        pk=participation_id,
        employee=request.user.employee
    )
    
    # Only allow cancellation if status is 'Registered'
    if participation.status != 'Registered':
        messages.error(request, 'You cannot cancel your registration at this stage')
        return redirect('my_training')
    
    if request.method == 'POST':
        participation.status = 'Cancelled'
        participation.save()
        messages.success(request, f'Your registration for "{participation.course.course_name}" has been cancelled')
        return redirect('my_training')
    
    return render(request, 'training/cancel_registration.html', {
        'participation': participation,
        'course': participation.course
    })

@login_required
def provide_feedback(request, participation_id):
    """Provide feedback for a completed course"""
    participation = get_object_or_404(
        TrainingParticipation, 
        pk=participation_id,
        employee=request.user.employee
    )
    
    # Check if course is completed
    if participation.status != 'Completed':
        messages.error(request, 'You can only provide feedback for completed courses')
        return redirect('my_training')
    
    if request.method == 'POST':
        feedback = request.POST.get('feedback', '')
        participation.feedback = feedback
        participation.save()
        messages.success(request, 'Thank you for providing your feedback')
        return redirect('my_training')
    
    return render(request, 'training/provide_feedback.html', {
        'participation': participation,
        'course': participation.course
    })

@login_required
@employee_approved_required
def my_training(request):
    """View my training courses (for employees)"""
    if not request.user.employee:
        messages.error(request, 'You do not have an employee profile')
        return redirect('dashboard')
    
    # Filter participations
    status_filter = request.GET.get('status', '')
    
    participations = TrainingParticipation.objects.filter(
        employee=request.user.employee
    ).select_related('course').order_by('-course__start_date')
    
    if status_filter:
        participations = participations.filter(status=status_filter)
    
    # Group participations by status
    upcoming = [p for p in participations if p.status == 'Registered']
    ongoing = [p for p in participations if p.status == 'Participating']
    completed = [p for p in participations if p.status == 'Completed']
    cancelled = [p for p in participations if p.status == 'Cancelled']
    
    return render(request, 'training/my_training.html', {
        'upcoming': upcoming,
        'ongoing': ongoing,
        'completed': completed,
        'cancelled': cancelled,
        'status_filter': status_filter
    })

@login_required
@hr_required
def training_admin(request):
    """Training administration dashboard"""
    # Get overall statistics
    total_courses = TrainingCourse.objects.count()
    active_courses = TrainingCourse.objects.filter(
        status__in=['Preparing', 'In Progress']
    ).count()
    completed_courses = TrainingCourse.objects.filter(status='Completed').count()
    
    total_participants = TrainingParticipation.objects.count()
    completed_participants = TrainingParticipation.objects.filter(status='Completed').count()
    
    # Get recently added courses
    recent_courses = TrainingCourse.objects.order_by('-created_date')[:5]
    
    # Get top courses by participation
    top_courses = TrainingCourse.objects.annotate(
        participant_count=Count('trainingparticipation')
    ).order_by('-participant_count')[:5]
    
    # Get upcoming courses
    today = date.today()
    upcoming_courses = TrainingCourse.objects.filter(
        start_date__gt=today
    ).order_by('start_date')[:5]
    
    # Get courses in progress
    in_progress_courses = TrainingCourse.objects.filter(
        status='In Progress'
    ).order_by('-start_date')[:5]
    
    return render(request, 'training/training_admin.html', {
        'total_courses': total_courses,
        'active_courses': active_courses,
        'completed_courses': completed_courses,
        'total_participants': total_participants,
        'completed_participants': completed_participants,
        'recent_courses': recent_courses,
        'top_courses': top_courses,
        'upcoming_courses': upcoming_courses,
        'in_progress_courses': in_progress_courses
    })

@login_required
@check_module_permission('training', 'View')
def training_report(request):
    """Training reports and statistics"""
    # Filter parameters
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    department_id = request.GET.get('department', '')
    
    # Base query
    courses = TrainingCourse.objects.all()
    participations = TrainingParticipation.objects.all()
    
    # Apply filters
    if date_from:
        courses = courses.filter(start_date__gte=date_from)
        participations = participations.filter(course__start_date__gte=date_from)
        
    if date_to:
        courses = courses.filter(end_date__lte=date_to)
        participations = participations.filter(course__end_date__lte=date_to)
    
    if department_id:
        # Only include participations from this department
        participations = participations.filter(employee__department_id=department_id)
    
    # Calculate statistics
    total_courses = courses.count()
    total_participations = participations.count()
    
    # Training by status
    courses_by_status = courses.values('status').annotate(count=Count('course_id'))
    participants_by_status = participations.values('status').annotate(count=Count('participation_id'))
    
    # Training by department
    department_stats = participations.values(
        'employee__department__department_name'
    ).annotate(
        count=Count('participation_id'),
        completed=Count('participation_id', filter=Q(status='Completed')),
        participating=Count('participation_id', filter=Q(status='Participating')),
        registered=Count('participation_id', filter=Q(status='Registered')),
        cancelled=Count('participation_id', filter=Q(status='Cancelled'))
    ).order_by('-count')
    
    # Cost statistics
    total_cost = courses.aggregate(Sum('cost'))['cost__sum'] or 0
    avg_cost_per_course = total_cost / total_courses if total_courses > 0 else 0
    avg_cost_per_participant = total_cost / total_participations if total_participations > 0 else 0
    
    # Get all departments for filter
    departments = Department.objects.filter(status=1)
    
    return render(request, 'training/training_report.html', {
        'date_from': date_from,
        'date_to': date_to,
        'department_id': department_id,
        'departments': departments,
        'total_courses': total_courses,
        'total_participations': total_participations,
        'courses_by_status': courses_by_status,
        'participants_by_status': participants_by_status,
        'department_stats': department_stats,
        'total_cost': total_cost,
        'avg_cost_per_course': avg_cost_per_course,
        'avg_cost_per_participant': avg_cost_per_participant
    })

@login_required
@check_module_permission('training', 'View')
def employee_training(request, employee_id):
    """View training history for a specific employee"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    # Get all training participations for this employee
    participations = TrainingParticipation.objects.filter(
        employee=employee
    ).select_related('course').order_by('-course__start_date')
    
    # Calculate statistics
    stats = {
        'total': participations.count(),
        'completed': participations.filter(status='Completed').count(),
        'participating': participations.filter(status='Participating').count(),
        'registered': participations.filter(status='Registered').count(),
        'cancelled': participations.filter(status='Cancelled').count(),
        'avg_score': participations.filter(score__isnull=False).aggregate(
            Avg('score')
        )['score__avg'] or 0
    }
    
    return render(request, 'training/employee_training.html', {
        'employee': employee,
        'participations': participations,
        'stats': stats
    })

@login_required
@check_module_permission('training', 'View')
def department_training(request, department_id):
    """View training statistics for a department"""
    department = get_object_or_404(Department, pk=department_id)
    
    # Get employees in this department
    employees = Employee.objects.filter(department=department, status='Working')
    
    # Get all training participations for this department
    participations = TrainingParticipation.objects.filter(
        employee__department=department
    ).select_related('course', 'employee')
    
    # Calculate overall statistics
    stats = {
        'total_employees': employees.count(),
        'trained_employees': participations.values('employee').distinct().count(),
        'total_participations': participations.count(),
        'completed': participations.filter(status='Completed').count(),
        'participating': participations.filter(status='Participating').count(),
        'registered': participations.filter(status='Registered').count(),
        'cancelled': participations.filter(status='Cancelled').count(),
        'avg_score': participations.filter(score__isnull=False).aggregate(
            Avg('score')
        )['score__avg'] or 0
    }
    
    # Calculate percentage of employees trained
    if stats['total_employees'] > 0:
        stats['training_coverage'] = (stats['trained_employees'] / stats['total_employees']) * 100
    else:
        stats['training_coverage'] = 0
    
    # Get most popular courses in this department
    popular_courses = TrainingCourse.objects.filter(
        trainingparticipation__employee__department=department
    ).annotate(
        participant_count=Count('trainingparticipation')
    ).order_by('-participant_count')[:5]
    
    return render(request, 'training/department_training.html', {
        'department': department,
        'employees': employees,
        'stats': stats,
        'popular_courses': popular_courses
    })

@login_required
@hr_required
def export_training(request):
    """Export training data to CSV or Excel"""
    export_type = request.GET.get('type', 'courses')  # courses or participants
    file_format = request.GET.get('format', 'csv')  # csv or excel
    
    if export_type == 'courses':
        # Export courses data
        if file_format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="training_courses.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'Course ID', 'Course Name', 'Description', 'Start Date', 'End Date',
                'Location', 'Cost', 'Organizer', 'Supervisor', 'Status',
                'Participants', 'Created Date'
            ])
            
            courses = TrainingCourse.objects.all().order_by('-created_date')
            for course in courses:
                participant_count = TrainingParticipation.objects.filter(course=course).count()
                writer.writerow([
                    course.course_id,
                    course.course_name,
                    course.description,
                    course.start_date.strftime('%Y-%m-%d') if course.start_date else '',
                    course.end_date.strftime('%Y-%m-%d') if course.end_date else '',
                    course.location,
                    course.cost,
                    course.organizer,
                    course.supervisor,
                    course.status,
                    participant_count,
                    course.created_date.strftime('%Y-%m-%d')
                ])
            
            return response
        
        elif file_format == 'excel':
            # Create Excel file
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output)
            worksheet = workbook.add_worksheet()
            
            # Add header
            headers = [
                'Course ID', 'Course Name', 'Description', 'Start Date', 'End Date',
                'Location', 'Cost', 'Organizer', 'Supervisor', 'Status',
                'Participants', 'Created Date'
            ]
            
            header_format = workbook.add_format({'bold': True, 'bg_color': '#3f51b5', 'color': 'white'})
            for col_num, header in enumerate(headers):
                worksheet.write(0, col_num, header, header_format)
            
            # Add data
            courses = TrainingCourse.objects.all().order_by('-created_date')
            for row_num, course in enumerate(courses, 1):
                participant_count = TrainingParticipation.objects.filter(course=course).count()
                
                row_data = [
                    course.course_id,
                    course.course_name,
                    course.description,
                    course.start_date.strftime('%Y-%m-%d') if course.start_date else '',
                    course.end_date.strftime('%Y-%m-%d') if course.end_date else '',
                    course.location,
                    course.cost,
                    course.organizer,
                    course.supervisor,
                    course.status,
                    participant_count,
                    course.created_date.strftime('%Y-%m-%d')
                ]
                
                for col_num, cell_data in enumerate(row_data):
                    worksheet.write(row_num, col_num, cell_data)
            
            workbook.close()
            output.seek(0)
            
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="training_courses.xlsx"'
            return response
    
    else:  # participants
        # Export participants data
        if file_format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="training_participants.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'ID', 'Employee', 'Employee ID', 'Department', 'Course', 
                'Registration Date', 'Status', 'Score', 'Achievement',
                'Certificate', 'Feedback'
            ])
            
            participations = TrainingParticipation.objects.all().select_related(
                'employee', 'course', 'employee__department'
            ).order_by('-registration_date')
            
            for participation in participations:
                writer.writerow([
                    participation.participation_id,
                    participation.employee.full_name,
                    participation.employee.employee_id,
                    participation.employee.department.department_name if participation.employee.department else '',
                    participation.course.course_name,
                    participation.registration_date.strftime('%Y-%m-%d'),
                    participation.status,
                    participation.score,
                    participation.achievement,
                    participation.certificate,
                    participation.feedback
                ])
            
            return response
        
        elif file_format == 'excel':
            # Create Excel file
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output)
            worksheet = workbook.add_worksheet()
            
            # Add header
            headers = [
                'ID', 'Employee', 'Employee ID', 'Department', 'Course', 
                'Registration Date', 'Status', 'Score', 'Achievement',
                'Certificate', 'Feedback'
            ]
            
            header_format = workbook.add_format({'bold': True, 'bg_color': '#3f51b5', 'color': 'white'})
            for col_num, header in enumerate(headers):
                worksheet.write(0, col_num, header, header_format)
            
            # Add data
            participations = TrainingParticipation.objects.all().select_related(
                'employee', 'course', 'employee__department'
            ).order_by('-registration_date')
            
            for row_num, participation in enumerate(participations, 1):
                row_data = [
                    participation.participation_id,
                    participation.employee.full_name,
                    participation.employee.employee_id,
                    participation.employee.department.department_name if participation.employee.department else '',
                    participation.course.course_name,
                    participation.registration_date.strftime('%Y-%m-%d'),
                    participation.status,
                    participation.score if participation.score else '',
                    participation.achievement if participation.achievement else '',
                    participation.certificate if participation.certificate else '',
                    participation.feedback if participation.feedback else ''
                ]
                
                for col_num, cell_data in enumerate(row_data):
                    worksheet.write(row_num, col_num, cell_data)
            
            workbook.close()
            output.seek(0)
            
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="training_participants.xlsx"'
            return response
    
    # If we get here, something went wrong
    messages.error(request, 'Invalid export parameters')
    return redirect('training_admin')



@login_required
@hr_required
def import_courses(request):
    """Import courses from CSV file"""
    if request.method == 'POST':
        form = BulkTrainingImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']
            
            # Process CSV file
            try:
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(decoded_file)
                
                success_count = 0
                error_count = 0
                errors = []
                
                for row in reader:
                    try:
                        # Create or update course
                        course, created = TrainingCourse.objects.update_or_create(
                            course_name=row.get('Course Name'),
                            defaults={
                                'description': row.get('Description', ''),
                                'start_date': row.get('Start Date') if row.get('Start Date') else None,
                                'end_date': row.get('End Date') if row.get('End Date') else None,
                                'location': row.get('Location', ''),
                                'cost': row.get('Cost', 0),
                                'organizer': row.get('Organizer', ''),
                                'supervisor': row.get('Supervisor', ''),
                                'status': row.get('Status', 'Preparing')
                            }
                        )
                        
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Row {reader.line_num}: {str(e)}")
                
                if error_count:
                    messages.warning(request, f'Imported {success_count} courses with {error_count} errors')
                else:
                    messages.success(request, f'Successfully imported {success_count} courses')
                
                return redirect('course_list')
                
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
                return redirect('import_courses')
    else:
        form = BulkTrainingImportForm()
    
    return render(request, 'training/import_courses.html', {'form': form})

@login_required
@hr_required
def import_participants(request):
    """Import participants from CSV file"""
    if request.method == 'POST':
        form = BulkTrainingImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']
            
            # Process CSV file
            try:
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(decoded_file)
                
                success_count = 0
                error_count = 0
                errors = []
                
                for row in reader:
                    try:
                        # Find employee and course
                        employee = Employee.objects.get(email=row.get('Employee Email'))
                        course = TrainingCourse.objects.get(course_name=row.get('Course Name'))
                        
                        # Create or update participation
                        participation, created = TrainingParticipation.objects.update_or_create(
                            employee=employee,
                            course=course,
                            defaults={
                                'registration_date': row.get('Registration Date') or date.today(),
                                'status': row.get('Status', 'Registered'),
                                'notes': row.get('Notes', '')
                            }
                        )
                        
                        success_count += 1
                    except Employee.DoesNotExist:
                        error_count += 1
                        errors.append(f"Row {reader.line_num}: Employee with email {row.get('Employee Email')} not found")
                    except TrainingCourse.DoesNotExist:
                        error_count += 1
                        errors.append(f"Row {reader.line_num}: Course '{row.get('Course Name')}' not found")
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Row {reader.line_num}: {str(e)}")
                
                if error_count:
                    messages.warning(request, f'Imported {success_count} participants with {error_count} errors')
                else:
                    messages.success(request, f'Successfully imported {success_count} participants')
                
                return redirect('training_admin')
                
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
                return redirect('import_participants')
    else:
        form = BulkTrainingImportForm()
    
    return render(request, 'training/import_participants.html', {'form': form})

@login_required
def training_calendar(request):
    """Calendar view for training courses"""
    return render(request, 'training/training_calendar.html')

@login_required
def training_calendar_data(request):
    """API endpoint for calendar data"""
    start_date = request.GET.get('start', '')
    end_date = request.GET.get('end', '')
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        # Default to current month
        today = date.today()
        start_date = date(today.year, today.month, 1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = date(today.year, today.month, last_day)
    
    # Initialize events list
    events = []
    
    # Get training courses in date range
    courses = TrainingCourse.objects.filter(
        (Q(start_date__gte=start_date) & Q(start_date__lte=end_date)) |
        (Q(end_date__gte=start_date) & Q(end_date__lte=end_date)) |
        (Q(start_date__lte=start_date) & Q(end_date__gte=end_date))
    )
    
    for course in courses:
        course_start = course.start_date if course.start_date else start_date
        course_end = course.end_date if course.end_date else course_start
        
        # Adjust end date for calendar display
        if course_end:
            display_end = (course_end + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            display_end = None
        
        # Select color based on status
        if course.status == 'Preparing':
            color = '#ffc107'  # Yellow
        elif course.status == 'In Progress':
            color = '#007bff'  # Blue
        elif course.status == 'Completed':
            color = '#28a745'  # Green
        else:  # Cancelled
            color = '#dc3545'  # Red
        
        # Create event
        event = {
            'id': f'course-{course.course_id}',
            'title': course.course_name,
            'start': course_start.strftime('%Y-%m-%d'),
            'end': display_end,
            'color': color,
            'textColor': '#fff',
            'url': f'/training/courses/{course.course_id}/'
        }
        
        events.append(event)
    
    # For employees or managers, include personal training enrollments
    if request.user.employee:
        employee = request.user.employee
        
        # Get participations
        participations = TrainingParticipation.objects.filter(
            employee=employee,
            course__start_date__gte=start_date,
            course__start_date__lte=end_date
        ).select_related('course')
        
        for participation in participations:
            # Create a personal event
            if participation.course.start_date:
                personal_event = {
                    'id': f'participation-{participation.participation_id}',
                    'title': f'My Training: {participation.course.course_name}',
                    'start': participation.course.start_date.strftime('%Y-%m-%d'),
                    'color': '#6f42c1',  # Purple for personal events
                    'textColor': '#fff',
                    'url': f'/training/courses/{participation.course.course_id}/'
                }
                
                events.append(personal_event)
    
    return JsonResponse({'events': events})

@login_required
def api_course_participants(request, course_id):
    """API endpoint for course participants"""
    course = get_object_or_404(TrainingCourse, pk=course_id)
    
    # Check permissions
    if not (request.user.role in ['HR', 'Admin'] or 
            (request.user.role == 'Manager' and request.user.employee and 
             request.user.employee.department == course.department)):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    participants = TrainingParticipation.objects.filter(course=course).select_related('employee')
    
    # Transform to JSON
    participants_data = []
    for p in participants:
        participants_data.append({
            'id': p.participation_id,
            'employee_id': p.employee.employee_id,
            'employee_name': p.employee.full_name,
            'department': p.employee.department.department_name if p.employee.department else None,
            'status': p.status,
            'registration_date': p.registration_date.strftime('%Y-%m-%d'),
            'score': p.score
        })
    
    return JsonResponse({'participants': participants_data})

@login_required
@check_module_permission('training', 'View')
def training_list(request):
    """List all training courses with filtering options"""
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    # Base query
    courses = TrainingCourse.objects.all().order_by('-start_date')
    
    # Apply filters
    if query:
        courses = courses.filter(
            Q(course_name__icontains=query) |
            Q(trainer__icontains=query) |
            Q(description__icontains=query)
        )
    
    if status_filter:
        courses = courses.filter(status=status_filter)
    
    # Paginate results
    paginator = Paginator(courses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
    }
    
    return render(request, 'training/training_list.html', context)

@login_required
@check_module_permission('training', 'Add')
def training_create(request):
    """Create a new training course"""
    if request.method == 'POST':
        form = TrainingCourseForm(request.POST)
        if form.is_valid():
            training = form.save(commit=False)
            training.created_by = request.user
            training.save()
            
            # Log the action
            messages.success(request, _('Training course created successfully.'))
            return redirect('training_detail', pk=training.pk)
    else:
        form = TrainingCourseForm()
    
    context = {
        'form': form,
        'title': _('Create New Training Course'),
        'is_create': True
    }
    
    return render(request, 'training/training_form.html', context)

@login_required
@check_module_permission('training', 'View')
def training_detail(request, pk):
    """View details of a specific training course including participants"""
    training = get_object_or_404(TrainingCourse, pk=pk)
    
    # Get participants
    participants = TrainingParticipation.objects.filter(course=training).select_related('employee')
    
    # Calculate statistics
    total_participants = participants.count()
    completed_count = participants.filter(status='Completed').count()
    pending_count = participants.filter(status='Pending').count()
    in_progress_count = participants.filter(status='In Progress').count()
    withdrawn_count = participants.filter(status='Withdrawn').count()
    
    completion_rate = (completed_count / total_participants * 100) if total_participants > 0 else 0
    
    context = {
        'training': training,
        'participants': participants,
        'total_participants': total_participants,
        'completed_count': completed_count,
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'withdrawn_count': withdrawn_count,
        'completion_rate': completion_rate,
    }
    
    return render(request, 'training/training_detail.html', context)

@login_required
@check_module_permission('training', 'Edit')
def training_edit(request, pk):
    """Edit an existing training course"""
    training = get_object_or_404(TrainingCourse, pk=pk)
    
    if request.method == 'POST':
        form = TrainingCourseForm(request.POST, instance=training)
        if form.is_valid():
            training = form.save()
            
            # Notify participants of any changes
            participants = TrainingParticipation.objects.filter(course=training)
            for participant in participants:
                if participant.employee.user:
                    create_notification(
                        user=participant.employee.user,
                        notification_type='Info',
                        title=_('Training Updated'),
                        message=_('A training course you are enrolled in has been updated: {}').format(training.course_name),
                        link=reverse('training_detail', args=[training.pk])
                    )
            
            messages.success(request, _('Training course updated successfully.'))
            return redirect('training_detail', pk=training.pk)
    else:
        form = TrainingCourseForm(instance=training)
    
    context = {
        'form': form,
        'training': training,
        'title': _('Edit Training Course'),
        'is_create': False
    }
    
    return render(request, 'training/training_form.html', context)

@login_required
@check_module_permission('training', 'Delete')
def training_delete(request, pk):
    """Delete a training course"""
    training = get_object_or_404(TrainingCourse, pk=pk)
    
    if request.method == 'POST':
        # Check if there are participants
        participants_exist = TrainingParticipation.objects.filter(course=training).exists()
        
        if participants_exist and not request.POST.get('confirm_delete'):
            messages.warning(request, _('This training has participants. Please confirm deletion.'))
            return redirect('training_delete', pk=training.pk)
        
        # Notify participants of cancellation
        participants = TrainingParticipation.objects.filter(course=training)
        for participant in participants:
            if participant.employee.user:
                create_notification(
                    user=participant.employee.user,
                    notification_type='Warning',
                    title=_('Training Cancelled'),
                    message=_('A training course you were enrolled in has been cancelled: {}').format(training.course_name),
                )
        
        # Delete the training and all related participations
        training.delete()
        messages.success(request, _('Training course deleted successfully.'))
        return redirect('training_list')
    
    context = {
        'training': training,
        'participants_exist': TrainingParticipation.objects.filter(course=training).exists()
    }
    
    return render(request, 'training/training_confirm_delete.html', context)

@login_required
@check_module_permission('training', 'Edit')
def add_participant(request, pk):
    """Add a participant to a training course"""
    training = get_object_or_404(TrainingCourse, pk=pk)
    
    if request.method == 'POST':
        employee_ids = request.POST.getlist('employees')
        
        if not employee_ids:
            messages.warning(request, _('No employees selected.'))
            return redirect('training_detail', pk=training.pk)
        
        # Add each selected employee as a participant
        added_count = 0
        for employee_id in employee_ids:
            try:
                employee = Employee.objects.get(pk=employee_id)
                
                # Check if already enrolled
                if not TrainingParticipation.objects.filter(course=training, employee=employee).exists():
                    participation = TrainingParticipation(
                        course=training,
                        employee=employee,
                        status='Pending'
                    )
                    participation.save()
                    added_count += 1
                    
                    # Notify the employee
                    if employee.user:
                        create_notification(
                            user=employee.user,
                            notification_type='Info',
                            title=_('New Training Enrollment'),
                            message=_('You have been enrolled in a new training course: {}').format(training.course_name),
                            link=reverse('training_detail', args=[training.pk])
                        )
            except Employee.DoesNotExist:
                continue
        
        if added_count > 0:
            messages.success(request, _('Added {} participants to the training.').format(added_count))
        else:
            messages.info(request, _('No new participants were added.'))
        
        return redirect('training_detail', pk=training.pk)
    
    # Get eligible employees (not yet enrolled)
    enrolled_employees = TrainingParticipation.objects.filter(course=training).values_list('employee_id', flat=True)
    available_employees = Employee.objects.exclude(employee_id__in=enrolled_employees).filter(status='Working')
    
    context = {
        'training': training,
        'available_employees': available_employees
    }
    
    return render(request, 'training/add_participants.html', context)

@login_required
@check_module_permission('training', 'Edit')
def remove_participant(request, pk):
    """Remove a participant from a training course"""
    participation = get_object_or_404(TrainingParticipation, pk=pk)
    training = participation.course
    
    if request.method == 'POST':
        # Notify the employee
        if participation.employee.user:
            create_notification(
                user=participation.employee.user,
                notification_type='Warning',
                title=_('Training Enrollment Removed'),
                message=_('You have been removed from the training course: {}').format(training.course_name)
            )
        
        # Delete participation
        participation.delete()
        messages.success(request, _('Participant removed successfully.'))
        
        return redirect('training_detail', pk=training.pk)
    
    context = {
        'participation': participation,
        'training': training
    }
    
    return render(request, 'training/remove_participant_confirm.html', context)


