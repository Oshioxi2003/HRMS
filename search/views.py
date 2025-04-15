from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from employee.models import Employee, Department, Position
from leave.models import LeaveRequest
from attendance.models import Attendance
from tasks.models import Task
from contract.models import EmploymentContract
from performance.models import EmployeeEvaluation
from documents.models import Document, DocumentCategory
from accounts.decorators import hr_required, check_module_permission

@login_required
def search(request):
    """Basic search that redirects to appropriate specific search view"""
    query = request.GET.get('q', '')
    search_type = request.GET.get('type', 'global')
    
    if not query:
        return render(request, 'search/search_home.html')
    
    if search_type == 'employee':
        return employee_search(request)
    elif search_type == 'document':
        return document_search(request)
    else:
        return global_search(request)

@login_required
def global_search(request):
    """Search across all entities"""
    query = request.GET.get('q', '')
    
    # Initialize results
    employee_results = []
    document_results = []
    leave_results = []
    attendance_results = []
    task_results = []
    
    if query:
        # Search employees
        employee_results = Employee.objects.filter(
            Q(full_name__icontains=query) | 
            Q(email__icontains=query) | 
            Q(phone__icontains=query) |
            Q(id_card__icontains=query)
        ).select_related('department', 'position')[:5]
        
        # Search documents
        document_results = Document.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__icontains=query)
        ).select_related('category')[:5]
        
        # Search leave requests
        if request.user.role in ['HR', 'Admin'] or request.user.role == 'Manager':
            # HR, Admin and Managers can see more leave requests
            if request.user.role in ['HR', 'Admin']:
                leave_results = LeaveRequest.objects.filter(
                    Q(employee__full_name__icontains=query) |
                    Q(reason__icontains=query)
                ).select_related('employee')[:5]
            elif request.user.role == 'Manager' and request.user.employee and request.user.employee.department:
                leave_results = LeaveRequest.objects.filter(
                    Q(employee__full_name__icontains=query) |
                    Q(reason__icontains=query),
                    employee__department=request.user.employee.department
                ).select_related('employee')[:5]
        else:
            # Regular employees can only see their own leave requests
            if request.user.employee:
                leave_results = LeaveRequest.objects.filter(
                    Q(reason__icontains=query),
                    employee=request.user.employee
                )[:5]
        
        # Search tasks
        if request.user.role in ['HR', 'Admin']:
            # HR and Admin can see all tasks
            task_results = Task.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            ).select_related('assignee')[:5]
        elif request.user.role == 'Manager' and request.user.employee and request.user.employee.department:
            # Managers can see tasks in their department
            task_results = Task.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query),
                department=request.user.employee.department
            ).select_related('assignee')[:5]
        else:
            # Regular employees can see tasks assigned to them
            if request.user.employee:
                task_results = Task.objects.filter(
                    Q(title__icontains=query) |
                    Q(description__icontains=query),
                    assignee=request.user.employee
                )[:5]
    
    # Count total results
    total_results = len(employee_results) + len(document_results) + len(leave_results) + len(task_results)
    
    return render(request, 'search/global_search.html', {
        'query': query,
        'employee_results': employee_results,
        'document_results': document_results,
        'leave_results': leave_results,
        'task_results': task_results,
        'total_results': total_results
    })

@login_required
def employee_search(request):
    """Search for employees"""
    query = request.GET.get('q', '')
    department_filter = request.GET.get('department', '')
    position_filter = request.GET.get('position', '')
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', 'name')
    
    employees = Employee.objects.all()
    
    # Apply search query
    if query:
        employees = employees.filter(
            Q(full_name__icontains=query) | 
            Q(email__icontains=query) | 
            Q(phone__icontains=query) |
            Q(id_card__icontains=query)
        )
    
    # Apply filters
    if department_filter:
        employees = employees.filter(department_id=department_filter)
    
    if position_filter:
        employees = employees.filter(position_id=position_filter)
    
    if status_filter:
        employees = employees.filter(status=status_filter)
    
    # Apply sorting
    if sort_by == 'name':
        employees = employees.order_by('full_name')
    elif sort_by == 'department':
        employees = employees.order_by('department__department_name', 'full_name')
    elif sort_by == 'hire_date':
        employees = employees.order_by('-hire_date')
    elif sort_by == 'id':
        employees = employees.order_by('employee_id')
    
    # Get filter options
    departments = Department.objects.filter(status=1)
    positions = Position.objects.filter(status=1)
    status_options = [('Working', 'Working'), ('Resigned', 'Resigned'), ('On Leave', 'On Leave')]
    
    return render(request, 'search/employee_search.html', {
        'query': query,
        'employees': employees,
        'departments': departments,
        'positions': positions,
        'status_options': status_options,
        'department_filter': department_filter,
        'position_filter': position_filter,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'result_count': employees.count()
    })

@login_required
def document_search(request):
    """Search for documents"""
    query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')
    visibility_filter = request.GET.get('visibility', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base query - documents the user can access
    user = request.user
    
    if user.role in ['HR', 'Admin']:
        # HR and Admin can see all documents
        documents = Document.objects.all()
    elif user.role == 'Manager' and user.employee and user.employee.department:
        # Managers can see company documents, department documents for their department,
        # and their own private documents
        department = user.employee.department
        documents = Document.objects.filter(
            Q(visibility='Company') |
            (Q(visibility='Department') & Q(department=department)) |
            (Q(visibility='Private') & Q(uploaded_by=user))
        )
    else:
        # Regular employees can see company documents, their department's documents,
        # and their own private documents
        if user.employee and user.employee.department:
            department = user.employee.department
            documents = Document.objects.filter(
                Q(visibility='Company') |
                (Q(visibility='Department') & Q(department=department)) |
                (Q(visibility='Private') & Q(uploaded_by=user))
            )
        else:
            # Users without an employee profile or department can only see their own documents
            documents = Document.objects.filter(
                Q(visibility='Company') |
                (Q(visibility='Private') & Q(uploaded_by=user))
            )
    
    # Apply search query
    if query:
        documents = documents.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__icontains=query)
        )
    
    # Apply filters
    if category_filter:
        documents = documents.filter(category_id=category_filter)
    
    if visibility_filter:
        documents = documents.filter(visibility=visibility_filter)
    
    if date_from:
        documents = documents.filter(created_date__gte=date_from)
    
    if date_to:
        documents = documents.filter(created_date__lte=date_to)
    
    # Sort by most recent
    documents = documents.order_by('-created_date')
    
    # Get filter options
    categories = DocumentCategory.objects.all()
    visibility_options = [('Private', 'Private'), ('Department', 'Department'), ('Company', 'Company')]
    
    return render(request, 'search/document_search.html', {
        'query': query,
        'documents': documents,
        'categories': categories,
        'visibility_options': visibility_options,
        'category_filter': category_filter,
        'visibility_filter': visibility_filter,
        'date_from': date_from,
        'date_to': date_to,
        'result_count': documents.count()
    })

@login_required
@hr_required
def advanced_search(request):
    """Advanced search across multiple entities"""
    query = request.GET.get('q', '')
    entity_type = request.GET.get('type', 'employee')
    department_filter = request.GET.get('department', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    results = []
    departments = Department.objects.filter(status=1)
    
    if query or department_filter or status_filter or date_from or date_to:
        if entity_type == 'employee':
            employee_q = Q()
            if query:
                employee_q = Q(full_name__icontains=query) | Q(email__icontains=query) | Q(id_card__icontains=query) | Q(phone__icontains=query)
            
            # Apply department filter
            if department_filter:
                employee_q &= Q(department_id=department_filter)
            
            # Apply status filter
            if status_filter:
                employee_q &= Q(status=status_filter)
            
            # Apply date filters (for hire date)
            if date_from:
                employee_q &= Q(hire_date__gte=date_from)
            if date_to:
                employee_q &= Q(hire_date__lte=date_to)
            
            # Execute query
            results = Employee.objects.filter(employee_q).select_related('department', 'position')
            
        elif entity_type == 'leave':
            leave_q = Q()
            if query:
                leave_q = Q(employee__full_name__icontains=query) | Q(reason__icontains=query)
            
            # Apply department filter
            if department_filter:
                leave_q &= Q(employee__department_id=department_filter)
            
            # Apply status filter
            if status_filter:
                leave_q &= Q(status=status_filter)
            
            # Apply date filters
            if date_from:
                leave_q &= Q(start_date__gte=date_from)
            if date_to:
                leave_q &= Q(end_date__lte=date_to)
            
            # Execute query
            results = LeaveRequest.objects.filter(leave_q).select_related('employee', 'employee__department')
            
        elif entity_type == 'attendance':
            attendance_q = Q()
            if query:
                attendance_q = Q(employee__full_name__icontains=query)
            
            # Apply department filter
            if department_filter:
                attendance_q &= Q(employee__department_id=department_filter)
            
            # Apply status filter
            if status_filter:
                attendance_q &= Q(status=status_filter)
            
            # Apply date filters
            if date_from:
                attendance_q &= Q(work_date__gte=date_from)
            if date_to:
                attendance_q &= Q(work_date__lte=date_to)
            
            # Execute query
            results = Attendance.objects.filter(attendance_q).select_related('employee', 'employee__department')
            
        elif entity_type == 'task':
            task_q = Q()
            if query:
                task_q = Q(title__icontains=query) | Q(description__icontains=query) | Q(assignee__full_name__icontains=query)
            
            # Apply department filter
            if department_filter:
                task_q &= Q(department_id=department_filter)
            
            # Apply status filter
            if status_filter:
                task_q &= Q(status=status_filter)
            
            # Apply date filters
            if date_from:
                task_q &= Q(due_date__gte=date_from)
            if date_to:
                task_q &= Q(due_date__lte=date_to)
            
            # Execute query
            results = Task.objects.filter(task_q).select_related('assignee', 'assignee__department')
            
        elif entity_type == 'contract':
            contract_q = Q()
            if query:
                contract_q = Q(employee__full_name__icontains=query)
            
            # Apply department filter
            if department_filter:
                contract_q &= Q(employee__department_id=department_filter)
            
            # Apply status filter
            if status_filter:
                contract_q &= Q(status=status_filter)
            
            # Apply date filters
            if date_from:
                contract_q &= Q(start_date__gte=date_from)
            if date_to:
                contract_q &= Q(end_date__lte=date_to)
            
            # Execute query
            results = EmploymentContract.objects.filter(contract_q).select_related('employee', 'employee__department')
    
    # Get status options based on entity type
    status_options = []
    if entity_type == 'employee':
        status_options = [('Working', 'Working'), ('Resigned', 'Resigned'), ('On Leave', 'On Leave')]
    elif entity_type == 'leave':
        status_options = [('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected'), ('Cancelled', 'Cancelled')]
    elif entity_type == 'attendance':
        status_options = [('Present', 'Present'), ('Absent', 'Absent'), ('On Leave', 'On Leave'), ('Holiday', 'Holiday')]
    elif entity_type == 'task':
        status_options = [('Not Started', 'Not Started'), ('In Progress', 'In Progress'), ('Completed', 'Completed'), ('On Hold', 'On Hold')]
    elif entity_type == 'contract':
        status_options = [('Active', 'Active'), ('Expired', 'Expired'), ('Terminated', 'Terminated')]
    
    return render(request, 'search/advanced_search.html', {
        'query': query,
        'entity_type': entity_type,
        'results': results,
        'departments': departments,
        'department_filter': department_filter,
        'status_filter': status_filter,
        'status_options': status_options,
        'date_from': date_from,
        'date_to': date_to,
        'result_count': len(results)
    })
