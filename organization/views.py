from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from employee.models import Employee, Department, Position
from accounts.decorators import check_module_permission, hr_required, manager_required
from accounts.models import User
from django.utils import timezone
import json

@login_required
@check_module_permission('organization', 'View')
def organization_chart(request):
    """Display organizational chart"""
    # Get all departments
    departments = Department.objects.filter(status=1).annotate(
        employee_count=Count('employee', filter=Q(employee__status='Working'))
    )
    
    # Get top management (employees without a direct manager but with management positions)
    top_management = Employee.objects.filter(
        status='Working',
        position__position_name__icontains='Director'
    ).order_by('position__position_name')
    
    # Build organization structure
    org_data = []
    
    # Add CEO/top management
    for manager in top_management:
        manager_data = {
            'id': f"emp-{manager.employee_id}",
            'name': manager.full_name,
            'title': manager.position.position_name if manager.position else 'Director',
            'img': manager.profile_image.url if manager.profile_image else None,
            'children': []
        }
        
        # Add departments under this manager
        if manager.department:
            # This is a department head, add only their department
            dept_data = build_department_data(manager.department)
            manager_data['children'].append(dept_data)
        else:
            # This is likely the CEO, add all departments
            for dept in departments:
                dept_data = build_department_data(dept)
                manager_data['children'].append(dept_data)
        
        org_data.append(manager_data)
    
    # If no top management found, create organization structure by departments
    if not org_data:
        for dept in departments:
            dept_data = build_department_data(dept)
            org_data.append(dept_data)
    
    return render(request, 'organization/org_chart.html', {
        'org_data': org_data,
        'departments': departments
    })

def build_department_data(department):
    """Build department data structure for org chart"""
    # Get department head (manager)
    department_head = Employee.objects.filter(
        department=department,
        position__position_name__icontains='Manager',
        status='Working'
    ).first()
    
    # If no explicit manager, get any employee with manager in their title
    if not department_head:
        department_head = Employee.objects.filter(
            department=department,
            position__position_name__icontains='Manager',
            status='Working'
        ).first()
    
    # Get employees in this department
    employees = Employee.objects.filter(
        department=department,
        status='Working'
    ).exclude(
        pk=department_head.pk if department_head else None
    ).order_by('position__position_name')
    
    # Create department node
    dept_data = {
        'id': f"dept-{department.department_id}",
        'name': department.department_name,
        'title': 'Department',
        'className': 'department',
        'children': []
    }
    
    # Add department head if exists
    if department_head:
        head_data = {
            'id': f"emp-{department_head.employee_id}",
            'name': department_head.full_name,
            'title': department_head.position.position_name if department_head.position else 'Manager',
            'img': department_head.profile_image.url if department_head.profile_image else None,
            'children': []
        }
        dept_data['children'].append(head_data)
        
        # Add staff under department head
        for employee in employees:
            emp_data = {
                'id': f"emp-{employee.employee_id}",
                'name': employee.full_name,
                'title': employee.position.position_name if employee.position else 'Staff',
                'img': employee.profile_image.url if employee.profile_image else None
            }
            head_data['children'].append(emp_data)
    else:
        # No department head, add employees directly to department
        for employee in employees:
            emp_data = {
                'id': f"emp-{employee.employee_id}",
                'name': employee.full_name,
                'title': employee.position.position_name if employee.position else 'Staff',
                'img': employee.profile_image.url if employee.profile_image else None
            }
            dept_data['children'].append(emp_data)
    
    return dept_data

@login_required
@check_module_permission('organization', 'View')
def organization_structure(request):
    """Display organizational structure hierarchy"""
    # Get all departments with employee counts
    departments = Department.objects.filter(status=1).annotate(
        employee_count=Count('employee', filter=Q(employee__status='Working')),
        average_salary=Sum('employee__contract__base_salary', filter=Q(employee__status='Working')) / 
                        Count('employee', filter=Q(employee__status='Working'))
    )
    
    # Get positions with counts
    positions = Position.objects.filter(status=1).annotate(
        employee_count=Count('employee', filter=Q(employee__status='Working'))
    ).order_by('-employee_count')
    
    # Get department statistics
    dept_stats = {
        'total_departments': departments.count(),
        'total_positions': positions.count(),
        'largest_department': departments.order_by('-employee_count').first() if departments.exists() else None,
        'positions_by_department': {}
    }
    
    # Get positions by department
    for dept in departments:
        dept_positions = Position.objects.filter(
            employee__department=dept,
            employee__status='Working'
        ).distinct().annotate(
            position_count=Count('employee', filter=Q(employee__status='Working', employee__department=dept))
        ).order_by('-position_count')
        
        dept_stats['positions_by_department'][dept.department_id] = dept_positions
    
    return render(request, 'organization/organization_structure.html', {
        'departments': departments,
        'positions': positions,
        'dept_stats': dept_stats
    })

@login_required
@hr_required
def edit_organization_structure(request):
    """Edit organizational structure (HR only)"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Handle department management
        if action == 'add_department':
            department_name = request.POST.get('department_name')
            department_code = request.POST.get('department_code')
            description = request.POST.get('description')
            
            # Validate inputs
            if not department_name or not department_code:
                messages.error(request, "Department name and code are required")
                return redirect('edit_organization_structure')
            
            # Check if department code is unique
            if Department.objects.filter(department_code=department_code).exists():
                messages.error(request, f"Department code '{department_code}' is already in use")
                return redirect('edit_organization_structure')
            
            # Create department
            department = Department.objects.create(
                department_name=department_name,
                department_code=department_code,
                description=description,
                status=1
            )
            
            messages.success(request, f"Department '{department_name}' created successfully")
            return redirect('edit_organization_structure')
            
        elif action == 'edit_department':
            department_id = request.POST.get('department_id')
            department_name = request.POST.get('department_name')
            department_code = request.POST.get('department_code')
            description = request.POST.get('description')
            
            # Get department
            department = get_object_or_404(Department, department_id=department_id)
            
            # Validate department code uniqueness if changed
            if department_code != department.department_code and Department.objects.filter(department_code=department_code).exists():
                messages.error(request, f"Department code '{department_code}' is already in use")
                return redirect('edit_organization_structure')
            
            # Update department
            department.department_name = department_name
            department.department_code = department_code
            department.description = description
            department.save()
            
            messages.success(request, f"Department '{department_name}' updated successfully")
            return redirect('edit_organization_structure')
            
        elif action == 'deactivate_department':
            department_id = request.POST.get('department_id')
            department = get_object_or_404(Department, department_id=department_id)
            
            # Check if department has employees
            if Employee.objects.filter(department=department, status='Working').exists():
                messages.error(request, f"Cannot deactivate department '{department.department_name}' as it has active employees")
                return redirect('edit_organization_structure')
            
            # Deactivate department
            department.status = 0
            department.save()
            
            messages.success(request, f"Department '{department.department_name}' deactivated successfully")
            return redirect('edit_organization_structure')
        
        # Handle position management
        elif action == 'add_position':
            position_name = request.POST.get('position_name')
            position_code = request.POST.get('position_code')
            description = request.POST.get('description')
            
            # Validate inputs
            if not position_name or not position_code:
                messages.error(request, "Position name and code are required")
                return redirect('edit_organization_structure')
            
            # Check if position code is unique
            if Position.objects.filter(position_code=position_code).exists():
                messages.error(request, f"Position code '{position_code}' is already in use")
                return redirect('edit_organization_structure')
            
            # Create position
            position = Position.objects.create(
                position_name=position_name,
                position_code=position_code,
                description=description,
                status=1
            )
            
            messages.success(request, f"Position '{position_name}' created successfully")
            return redirect('edit_organization_structure')
            
        elif action == 'edit_position':
            position_id = request.POST.get('position_id')
            position_name = request.POST.get('position_name')
            position_code = request.POST.get('position_code')
            description = request.POST.get('description')
            
            # Get position
            position = get_object_or_404(Position, position_id=position_id)
            
            # Validate position code uniqueness if changed
            if position_code != position.position_code and Position.objects.filter(position_code=position_code).exists():
                messages.error(request, f"Position code '{position_code}' is already in use")
                return redirect('edit_organization_structure')
            
            # Update position
            position.position_name = position_name
            position.position_code = position_code
            position.description = description
            position.save()
            
            messages.success(request, f"Position '{position_name}' updated successfully")
            return redirect('edit_organization_structure')
            
        elif action == 'deactivate_position':
            position_id = request.POST.get('position_id')
            position = get_object_or_404(Position, position_id=position_id)
            
            # Check if position has employees
            if Employee.objects.filter(position=position, status='Working').exists():
                messages.error(request, f"Cannot deactivate position '{position.position_name}' as it has active employees")
                return redirect('edit_organization_structure')
            
            # Deactivate position
            position.status = 0
            position.save()
            
            messages.success(request, f"Position '{position.position_name}' deactivated successfully")
            return redirect('edit_organization_structure')
    
    # For GET request
    departments = Department.objects.all().order_by('-status', 'department_name')
    positions = Position.objects.all().order_by('-status', 'position_name')
    
    return render(request, 'organization/edit_organization_structure.html', {
        'departments': departments,
        'positions': positions
    })

@login_required
@check_module_permission('organization', 'View')
def department_detail(request, department_id):
    """View detailed information about a department"""
    department = get_object_or_404(Department, department_id=department_id)
    
    # Get department head (manager)
    department_head = Employee.objects.filter(
        department=department,
        position__position_name__icontains='Manager',
        status='Working'
    ).first()
    
    # If no explicit manager, get any employee with manager in their title
    if not department_head:
        department_head = Employee.objects.filter(
            department=department,
            position__position_name__icontains='Manager',
            status='Working'
        ).first()
    
    # Get all employees in the department
    employees = Employee.objects.filter(
        department=department,
        status='Working'
    ).order_by('position__position_name', 'full_name')
    
    # Get employee count by position
    position_counts = {}
    for employee in employees:
        position_name = employee.position.position_name if employee.position else 'No Position'
        if position_name in position_counts:
            position_counts[position_name] += 1
        else:
            position_counts[position_name] = 1
    
    # Calculate department statistics
    total_employees = employees.count()
    male_count = employees.filter(gender='Male').count()
    female_count = employees.filter(gender='Female').count()
    other_count = employees.filter(gender='Other').count()
    
    gender_distribution = {
        'male': round(male_count / total_employees * 100 if total_employees > 0 else 0, 1),
        'female': round(female_count / total_employees * 100 if total_employees > 0 else 0, 1),
        'other': round(other_count / total_employees * 100 if total_employees > 0 else 0, 1)
    }
    
    # Get recent hires (last 3 months)
    three_months_ago = timezone.now().date() - timezone.timedelta(days=90)
    recent_hires = employees.filter(hire_date__gte=three_months_ago).order_by('-hire_date')
    
    return render(request, 'organization/department_detail.html', {
        'department': department,
        'department_head': department_head,
        'employees': employees,
        'total_employees': total_employees,
        'position_counts': position_counts,
        'gender_distribution': gender_distribution,
        'recent_hires': recent_hires
    })

@login_required
@check_module_permission('organization', 'View')
def department_members(request, department_id):
    """View all members of a department"""
    department = get_object_or_404(Department, department_id=department_id)
    
    # Get search parameters
    search_query = request.GET.get('q', '')
    position_filter = request.GET.get('position', '')
    
    # Get all employees in the department
    employees = Employee.objects.filter(
        department=department,
        status='Working'
    )
    
    # Apply search filter
    if search_query:
        employees = employees.filter(
            Q(full_name__icontains=search_query) | 
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    # Apply position filter
    if position_filter:
        employees = employees.filter(position_id=position_filter)
    
    # Order employees
    employees = employees.order_by('position__position_name', 'full_name')
    
    # Get positions in this department for filter
    positions = Position.objects.filter(
        employee__department=department,
        employee__status='Working'
    ).distinct()
    
    return render(request, 'organization/department_members.html', {
        'department': department,
        'employees': employees,
        'positions': positions,
        'search_query': search_query,
        'position_filter': position_filter
    })

@login_required
@manager_required
def my_team(request):
    """View my team (for managers)"""
    if not request.user.employee or not request.user.employee.department:
        messages.error(request, "You don't have a department assigned")
        return redirect('dashboard')
    
    department = request.user.employee.department
    manager = request.user.employee
    
    # Get all team members
    team_members = Employee.objects.filter(
        department=department,
        status='Working'
    ).exclude(pk=manager.pk).order_by('position__position_name', 'full_name')
    
    # Get search parameters
    search_query = request.GET.get('q', '')
    position_filter = request.GET.get('position', '')
    
    # Apply search filter
    if search_query:
        team_members = team_members.filter(
            Q(full_name__icontains=search_query) | 
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    # Apply position filter
    if position_filter:
        team_members = team_members.filter(position_id=position_filter)
    
    # Get positions in this department for filter
    positions = Position.objects.filter(
        employee__department=department,
        employee__status='Working'
    ).distinct()
    
    # Get team statistics
    total_members = team_members.count()
    position_counts = {}
    for member in team_members:
        position_name = member.position.position_name if member.position else 'No Position'
        if position_name in position_counts:
            position_counts[position_name] += 1
        else:
            position_counts[position_name] = 1
    
    # Get recent hires (last 3 months)
    three_months_ago = timezone.now().date() - timezone.timedelta(days=90)
    recent_hires = team_members.filter(hire_date__gte=three_months_ago).order_by('-hire_date')
    
    return render(request, 'organization/my_team.html', {
        'department': department,
        'manager': manager,
        'team_members': team_members,
        'positions': positions,
        'search_query': search_query,
        'position_filter': position_filter,
        'total_members': total_members,
        'position_counts': position_counts,
        'recent_hires': recent_hires
    })

@login_required
@manager_required
def my_team_structure(request):
    """View team structure (for managers)"""
    if not request.user.employee or not request.user.employee.department:
        messages.error(request, "You don't have a department assigned")
        return redirect('dashboard')
    
    department = request.user.employee.department
    manager = request.user.employee
    
    # Build team structure
    team_data = {
        'id': f"emp-{manager.employee_id}",
        'name': manager.full_name,
        'title': manager.position.position_name if manager.position else 'Manager',
        'img': manager.profile_image.url if manager.profile_image else None,
        'children': []
    }
    
    # Get team members
    team_members = Employee.objects.filter(
        department=department,
        status='Working'
    ).exclude(pk=manager.pk).order_by('position__position_name', 'full_name')
    
    # Group team members by position for better visualization
    positions = {}
    for member in team_members:
        position_name = member.position.position_name if member.position else 'Staff'
        
        if position_name not in positions:
            positions[position_name] = []
        
        positions[position_name].append(member)
    
    # Sort positions for hierarchical display
    sorted_positions = sorted(positions.keys(), key=lambda p: 'Manager' in p, reverse=True)
    
    # Add positions and employees to structure
    for position_name in sorted_positions:
        position_members = positions[position_name]
        
        # If only one person in this position, add directly
        if len(position_members) == 1:
            member = position_members[0]
            member_data = {
                'id': f"emp-{member.employee_id}",
                'name': member.full_name,
                'title': position_name,
                'img': member.profile_image.url if member.profile_image else None
            }
            team_data['children'].append(member_data)
        # If multiple people, group under position
        else:
            position_data = {
                'id': f"pos-{position_name.replace(' ', '-')}",
                'name': position_name,
                'title': f"{len(position_members)} members",
                'className': 'position',
                'children': []
            }
            
            for member in position_members:
                member_data = {
                    'id': f"emp-{member.employee_id}",
                    'name': member.full_name,
                    'title': position_name,
                    'img': member.profile_image.url if member.profile_image else None
                }
                position_data['children'].append(member_data)
            
            team_data['children'].append(position_data)
    
    return render(request, 'organization/my_team_structure.html', {
        'department': department,
        'manager': manager,
        'team_data': json.dumps([team_data])
    })
