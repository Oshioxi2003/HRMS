from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from django.utils.translation import gettext as _
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os

import csv
import json
from datetime import date, datetime
import xlwt
import settings
from django.conf import settings

from .models import (
    Employee, EmployeeLocation, Department, Position, AcademicTitle, 
    EducationLevel, InsuranceAndTax, CertificateType, EmployeeCertificate, EmployeeDocument
)
from .forms import (
    EmployeeForm, EmployeeProfileForm, EmployeeLocationForm, EmployeeBasicInfoForm,
    InsuranceAndTaxForm, CertificateTypeForm, EmployeeCertificateForm,
    DepartmentForm, PositionForm, AcademicTitleForm, EducationLevelForm
)
from accounts.decorators import hr_required, check_module_permission, admin_required
from notifications.services import create_notification
from messaging.services import EmailService
from core.export import ExportHelper
from accounts.models import *
# Employee views
@login_required
@check_module_permission('employee', 'View')
def employee_list(request):
    """List all employees with filtering"""
    query = request.GET.get('q', '')
    department_filter = request.GET.get('department', '')
    position_filter = request.GET.get('position', '')
    status_filter = request.GET.get('status', '')
    
    employees = Employee.objects.select_related('department', 'position').all()
    
    if query:
        employees = employees.filter(
            Q(full_name__icontains=query) |
            Q(email__icontains=query) |
            Q(id_card__icontains=query) |
            Q(phone__icontains=query)
        )
    
    if department_filter:
        employees = employees.filter(department_id=department_filter)
    
    if position_filter:
        employees = employees.filter(position_id=position_filter)
    
    if status_filter:
        employees = employees.filter(status=status_filter)
    
    # Order by name
    employees = employees.order_by('full_name')
    
    # Get counts for summary
    total_count = employees.count()
    active_count = employees.filter(status='Working').count()
    inactive_count = total_count - active_count
    
    # Paginate results
    paginator = Paginator(employees, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get list of departments and positions for filter dropdowns
    departments = Department.objects.filter(status=1).order_by('department_name')
    positions = Position.objects.filter(status=1).order_by('position_name')
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'departments': departments,
        'positions': positions,
        'department_filter': department_filter,
        'position_filter': position_filter,
        'status_filter': status_filter,
        'total_count': total_count,
        'active_count': active_count,
        'inactive_count': inactive_count
    }
    
    return render(request, 'employee/employee_list.html', context)

@login_required
@check_module_permission('employee', 'View')
def employee_detail(request, pk):
    """View employee details"""
    employee = get_object_or_404(Employee, pk=pk)
    
    # Get related information
    try:
        location = EmployeeLocation.objects.get(employee=employee)
    except EmployeeLocation.DoesNotExist:
        location = None
    
    try:
        insurance = InsuranceAndTax.objects.get(employee=employee)
    except InsuranceAndTax.DoesNotExist:
        insurance = None
    
    certificates = EmployeeCertificate.objects.filter(employee=employee).order_by('-issued_date')
    
    context = {
        'employee': employee,
        'location': location,
        'insurance': insurance,
        'certificates': certificates,
        # Add other related information as needed
    }
    
    return render(request, 'employee/employee_detail.html', context)

@login_required
@check_module_permission('employee', 'Edit')
def employee_create(request):
    """Create a new employee"""
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        location_form = EmployeeLocationForm(request.POST)
        
        if form.is_valid() and location_form.is_valid():
            employee = form.save(commit=False)
            
            # Auto-approve for Admin, HR, and Manager roles
            if hasattr(employee, 'user') and employee.user and employee.user.role in ['Admin', 'HR', 'Manager']:
                employee.approval_status = 'Approved'
                employee.approval_date = timezone.now()
            
            employee.save()
            
            # Save location information
            location = location_form.save(commit=False)
            location.employee = employee
            location.save()
            
            # Process document uploads
            process_document_uploads(request, employee)
            
            messages.success(request, _('Tạo nhân viên thành công.'))
            return redirect('employee_detail', pk=employee.pk)
    else:
        form = EmployeeForm()
        location_form = EmployeeLocationForm()
    
    context = {
        'form': form,
        'location_form': location_form,
        'is_create': True,
        'title': _('Create New Employee')
    }
    
    return render(request, 'employee/employee_form.html', context)

def process_document_uploads(request, employee):
    """Process document uploads for an employee"""
    document_fields = {
        'id_card_front': 'ID Card Front',
        'id_card_back': 'ID Card Back',
        'diploma': 'Diploma/Degree',
        'other_documents': 'Other Document'
    }
    
    for field_name, doc_type in document_fields.items():
        if field_name in request.FILES:
            uploaded_file = request.FILES[field_name]
            
            # Create document record
            document = EmployeeDocument(
                employee=employee,
                document_type=field_name,
                file=uploaded_file,
                file_name=uploaded_file.name,
                file_type=uploaded_file.content_type,
                file_size=uploaded_file.size // 1024  # Convert bytes to KB
            )
            document.save()
            
            # Log the document upload
            if hasattr(request, 'user') and request.user.is_authenticated:
                from accounts.models import SystemLog
                SystemLog.objects.create(
                    user=request.user,
                    action="Document Upload",
                    object_type="EmployeeDocument",
                    object_id=document.document_id,
                    details=f"Uploaded {doc_type} for {employee.full_name}"
                )

@login_required
@admin_required
def employee_approve(request, pk):
    """Approve or reject a pending employee"""
    employee = get_object_or_404(Employee, pk=pk)
    
    if employee.approval_status != 'Pending':
        messages.warning(request, _('Nhân viên này không trong trạng thái chờ phê duyệt.'))
        return redirect('employee_detail', pk=pk)
    
    if request.method == 'POST':
        approval_action = request.POST.get('approval_action')
        notes = request.POST.get('notes', '')
        
        if approval_action == 'approve':
            # Update employee status
            employee.approval_status = 'Approved'
            employee.approval_date = timezone.now()
            employee.approval_notes = notes
            employee.save()
            
            # Send approval email
            send_approval_email(employee, approved=True)
            
            # Create notification for employee if they have a user account
            try:
                user = User.objects.get(email=employee.email)
                create_notification(
                    user=user,
                    notification_type='Success',
                    title=_('Hồ sơ nhân viên đã được phê duyệt'),
                    message=_('Hồ sơ nhân viên của bạn đã được phê duyệt. Bạn có thể truy cập hệ thống ngay bây giờ.'),
                    link=reverse('employee_dashboard')
                )
            except User.DoesNotExist:
                pass
            
            messages.success(request, _('Nhân viên đã được phê duyệt thành công.'))
            
        elif approval_action == 'reject':
            # Update employee status
            employee.approval_status = 'Rejected'
            employee.approval_date = timezone.now()
            employee.approval_notes = notes
            employee.save()
            
            # Send rejection email
            send_approval_email(employee, approved=False)
            
            messages.warning(request, _('Nhân viên đã bị từ chối.'))
        
        return redirect('employee_detail', pk=pk)
    
    return render(request, 'employee/employee_approve.html', {'employee': employee})

def send_approval_email(employee, approved=True):
    """Send employee approval/rejection email"""
    if not employee.email:
        return
    
    if approved:
        subject = _('Hồ sơ nhân viên của bạn đã được phê duyệt')
        template = 'employee_approved'
    else:
        subject = _('Hồ sơ nhân viên của bạn cần được chỉnh sửa')
        template = 'employee_rejected'
    
    # Use messaging service if available
    try:
        # Get current year for footer
        current_year = timezone.now().year
        
        # Using template-based email service
        EmailService.send_email_by_template(
            template_code=template,
            to_email=employee.email,
            context_dict={
                'name': employee.full_name,
                'notes': employee.approval_notes or _('Không có ghi chú bổ sung'),
                'approval_date': employee.approval_date,
                'login_url': settings.SITE_URL + reverse('login'),
                'company_name': settings.COMPANY_NAME,
                'current_year': current_year
            }
        )
    except Exception as e:
        # Fallback to simple email
        from django.core.mail import send_mail
        
        message = _("Kính gửi {},\n\n").format(employee.full_name)
        
        if approved:
            message += _("Chúng tôi vui mừng thông báo rằng hồ sơ nhân viên của bạn đã được phê duyệt. Bạn có thể đăng nhập vào hệ thống bằng thông tin đăng nhập của mình.\n\n")
        else:
            message += _("Chúng tôi rất tiếc phải thông báo rằng hồ sơ nhân viên của bạn chưa được phê duyệt tại thời điểm này. Vui lòng xem bên dưới để biết thêm thông tin.\n\n")
        
        if employee.approval_notes:
            message += _("Ghi chú: {}\n\n").format(employee.approval_notes)
        
        message += _("Trân trọng,\nPhòng Nhân sự")
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [employee.email],
            fail_silently=True
        )

@login_required
@check_module_permission('employee', 'Edit')
def employee_update(request, pk):
    """Update an existing employee"""
    employee = get_object_or_404(Employee, pk=pk)
    
    # Get location if exists or prepare for new one
    try:
        location = EmployeeLocation.objects.get(employee=employee)
    except EmployeeLocation.DoesNotExist:
        location = None
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        location_form = EmployeeLocationForm(request.POST, instance=location)
        
        if form.is_valid() and location_form.is_valid():
            # Save employee
            employee = form.save()
            
            # Save or create location
            if location:
                location_form.save()
            else:
                location = location_form.save(commit=False)
                location.employee = employee
                location.save()
            
            messages.success(request, _('Cập nhật nhân viên thành công.'))
            return redirect('employee_detail', pk=employee.pk)
    else:
        form = EmployeeForm(instance=employee)
        location_form = EmployeeLocationForm(instance=location)
    
    context = {
        'form': form,
        'location_form': location_form,
        'is_create': False,
        'employee': employee,
        'title': _('Update Employee')
    }
    
    return render(request, 'employee/employee_form.html', context)

@login_required
@check_module_permission('employee', 'Delete')
def employee_delete(request, pk):
    """Delete an employee"""
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        employee_name = employee.full_name
        employee.delete()
        messages.success(request, _(f'Đã xóa nhân viên "{employee_name}" thành công.'))
        return redirect('employee_list')
    
    return render(request, 'employee/employee_confirm_delete.html', {'employee': employee})

# Location management
@login_required
@check_module_permission('employee', 'View')
def employee_location(request, employee_id):
    """View employee location details"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    try:
        location = EmployeeLocation.objects.get(employee=employee)
    except EmployeeLocation.DoesNotExist:
        location = None
    
    context = {
        'employee': employee,
        'location': location
    }
    
    return render(request, 'employee/employee_location.html', context)

@login_required
@check_module_permission('employee', 'Edit')
def employee_location_update(request, employee_id):
    """Update employee location"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    try:
        location = EmployeeLocation.objects.get(employee=employee)
    except EmployeeLocation.DoesNotExist:
        location = None
    
    if request.method == 'POST':
        form = EmployeeLocationForm(request.POST, instance=location)
        
        if form.is_valid():
            if location:
                form.save()
            else:
                location = form.save(commit=False)
                location.employee = employee
                location.save()
            
            messages.success(request, _('Thông tin vị trí đã được cập nhật thành công.'))
            return redirect('employee_detail', pk=employee_id)
    else:
        form = EmployeeLocationForm(instance=location)
    
    context = {
        'form': form,
        'employee': employee,
        'location': location,
        'title': _('Update Location Information')
    }
    
    return render(request, 'employee/location_form.html', context)

# Insurance and tax management
@login_required
@check_module_permission('employee', 'View')
def insurance_tax_detail(request, employee_id):
    """View insurance and tax details for an employee"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    try:
        insurance = InsuranceAndTax.objects.get(employee=employee)
    except InsuranceAndTax.DoesNotExist:
        insurance = None
    
    context = {
        'employee': employee,
        'insurance': insurance
    }
    
    return render(request, 'employee/insurance_tax_detail.html', context)

@login_required
@check_module_permission('employee', 'Edit')
def insurance_tax_create(request, employee_id):
    """Create insurance and tax information"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    # Check if record already exists
    if InsuranceAndTax.objects.filter(employee=employee).exists():
        messages.warning(request, _('Thông tin bảo hiểm và thuế cho nhân viên này đã tồn tại'))
        return redirect('insurance_tax_update', employee_id=employee_id)
    
    if request.method == 'POST':
        form = InsuranceAndTaxForm(request.POST)
        
        if form.is_valid():
            insurance = form.save(commit=False)
            insurance.employee = employee
            insurance.save()
            
            messages.success(request, _('Đã tạo thông tin bảo hiểm và thuế thành công.'))
            return redirect('employee_detail', pk=employee_id)
    else:
        form = InsuranceAndTaxForm()
    
    context = {
        'form': form,
        'employee': employee,
        'is_create': True,
        'title': _('Create Insurance & Tax Information')
    }
    
    return render(request, 'employee/insurance_tax_form.html', context)

@login_required
@check_module_permission('employee', 'Edit')
def insurance_tax_update(request, employee_id):
    """Update insurance and tax information"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    try:
        insurance = InsuranceAndTax.objects.get(employee=employee)
    except InsuranceAndTax.DoesNotExist:
        return redirect('insurance_tax_create', employee_id=employee_id)
    
    if request.method == 'POST':
        form = InsuranceAndTaxForm(request.POST, instance=insurance)
        
        if form.is_valid():
            form.save()
            messages.success(request, _('Đã cập nhật thông tin bảo hiểm và thuế thành công.'))
            return redirect('employee_detail', pk=employee_id)
    else:
        form = InsuranceAndTaxForm(instance=insurance)
    
    context = {
        'form': form,
        'employee': employee,
        'is_create': False,
        'title': _('Update Insurance & Tax Information')
    }
    
    return render(request, 'employee/insurance_tax_form.html', context)

# Certificate management
@login_required
@check_module_permission('employee', 'View')
def employee_certificates(request, employee_id):
    """View all certificates for an employee"""
    employee = get_object_or_404(Employee, pk=employee_id)
    certificates = EmployeeCertificate.objects.filter(employee=employee).order_by('-issued_date')
    
    context = {
        'employee': employee,
        'certificates': certificates
    }
    
    return render(request, 'employee/employee_certificates.html', context)

@login_required
@check_module_permission('employee', 'Edit')
def add_certificate(request, employee_id):
    """Add a new certificate for an employee"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    if request.method == 'POST':
        form = EmployeeCertificateForm(request.POST, request.FILES)
        
        if form.is_valid():
            certificate = form.save(commit=False)
            certificate.employee = employee
            
            # Auto-determine status based on expiry date
            if certificate.expiry_date:
                if certificate.expiry_date < date.today():
                    certificate.status = 'Expired'
                else:
                    certificate.status = 'Valid'
            
            certificate.save()
            messages.success(request, _('Đã thêm chứng chỉ thành công.'))
            return redirect('employee_certificates', employee_id=employee_id)
    else:
        form = EmployeeCertificateForm()
    
    context = {
        'form': form,
        'employee': employee,
        'title': _('Add Certificate')
    }
    
    return render(request, 'employee/certificate_form.html', context)

@login_required
@check_module_permission('employee', 'Edit')
def edit_certificate(request, certificate_id):
    """Edit an existing certificate"""
    certificate = get_object_or_404(EmployeeCertificate, pk=certificate_id)
    employee = certificate.employee
    
    if request.method == 'POST':
        form = EmployeeCertificateForm(request.POST, request.FILES, instance=certificate)
        
        if form.is_valid():
            certificate = form.save(commit=False)
            
            # Auto-determine status based on expiry date if not revoked
            if certificate.status != 'Revoked' and certificate.expiry_date:
                if certificate.expiry_date < date.today():
                    certificate.status = 'Expired'
                else:
                    certificate.status = 'Valid'
            
            certificate.save()
            messages.success(request, _('Đã cập nhật chứng chỉ thành công.'))
            return redirect('employee_certificates', employee_id=employee.pk)
    else:
        form = EmployeeCertificateForm(instance=certificate)
    
    context = {
        'form': form,
        'employee': employee,
        'certificate': certificate,
        'title': _('Edit Certificate')
    }
    
    return render(request, 'employee/certificate_form.html', context)

@login_required
@check_module_permission('employee', 'Delete')
def delete_certificate(request, certificate_id):
    """Delete a certificate"""
    certificate = get_object_or_404(EmployeeCertificate, pk=certificate_id)
    employee_id = certificate.employee.pk
    
    if request.method == 'POST':
        certificate.delete()
        messages.success(request, _('Đã xóa chứng chỉ thành công.'))
        return redirect('employee_certificates', employee_id=employee_id)
    
    context = {
        'certificate': certificate,
        'employee': certificate.employee
    }
    
    return render(request, 'employee/certificate_confirm_delete.html', context)

@login_required
def my_certificates(request):
    """View current user's certificates"""
    if not request.user.employee:
        messages.error(request, _('Bạn không có hồ sơ nhân viên.'))
        return redirect('dashboard')
    
    certificates = EmployeeCertificate.objects.filter(
        employee=request.user.employee
    ).order_by('-issued_date')
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        certificates = certificates.filter(status=status_filter)
    
    # Check for expiring certificates
    today = date.today()
    for cert in certificates:
        if cert.expiry_date and cert.status == 'Valid':
            days_until_expiry = (cert.expiry_date - today).days
            if days_until_expiry <= 30:
                cert.expiring_soon = True
                cert.days_until_expiry = days_until_expiry
    
    context = {
        'certificates': certificates,
        'status_filter': status_filter
    }
    
    return render(request, 'employee/my_certificates.html', context)

@login_required
def add_my_certificate(request):
    """Add a certificate for the current user"""
    if not request.user.employee:
        messages.error(request, _('Bạn không có hồ sơ nhân viên.'))
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = EmployeeCertificateForm(request.POST, request.FILES)
        
        if form.is_valid():
            certificate = form.save(commit=False)
            certificate.employee = request.user.employee
            
            # Auto-determine status based on expiry date
            if certificate.expiry_date:
                if certificate.expiry_date < date.today():
                    certificate.status = 'Expired'
                else:
                    certificate.status = 'Valid'
            
            certificate.save()
            
            # Notify HR about new certificate
            create_notification(
                role='HR',
                notification_type='Certificate',
                title=_('Đã thêm chứng chỉ mới'),
                message=f"{request.user.employee.full_name} đã thêm một chứng chỉ mới: {certificate.certificate_name}",
                link=reverse('edit_certificate', args=[certificate.certificate_id])
            )
            
            messages.success(request, _('Đã thêm chứng chỉ thành công.'))
            return redirect('my_certificates')
    else:
        form = EmployeeCertificateForm()
    
    context = {
        'form': form,
        'title': _('Add My Certificate')
    }
    
    return render(request, 'employee/certificate_form.html', context)

# Certificate type management
@login_required
@hr_required
def certificate_type_list(request):
    """List all certificate types"""
    certificate_types = CertificateType.objects.all().order_by('type_name')
    
    context = {
        'certificate_types': certificate_types
    }
    
    return render(request, 'employee/certificate_type_list.html', context)

@login_required
@hr_required
def certificate_type_create(request):
    """Create a new certificate type"""
    if request.method == 'POST':
        form = CertificateTypeForm(request.POST)
        
        if form.is_valid():
            form.save()
            messages.success(request, _('Đã tạo loại chứng chỉ thành công.'))
            return redirect('certificate_type_list')
    else:
        form = CertificateTypeForm()
    
    context = {
        'form': form,
        'title': _('Create Certificate Type')
    }
    
    return render(request, 'employee/certificate_type_form.html', context)

@login_required
@hr_required
def certificate_type_update(request, pk):
    """Update an existing certificate type"""
    certificate_type = get_object_or_404(CertificateType, pk=pk)
    
    if request.method == 'POST':
        form = CertificateTypeForm(request.POST, instance=certificate_type)
        
        if form.is_valid():
            form.save()
            messages.success(request, _('Đã cập nhật loại chứng chỉ thành công.'))
            return redirect('certificate_type_list')
    else:
        form = CertificateTypeForm(instance=certificate_type)
    
    context = {
        'form': form,
        'certificate_type': certificate_type,
        'title': _('Update Certificate Type')
    }
    
    return render(request, 'employee/certificate_type_form.html', context)

@login_required
@hr_required
def certificate_type_delete(request, pk):
    """Delete a certificate type"""
    certificate_type = get_object_or_404(CertificateType, pk=pk)
    
    # Check if certificate type is in use
    if EmployeeCertificate.objects.filter(type=certificate_type).exists():
        messages.error(request, _('Không thể xóa loại chứng chỉ đang được sử dụng.'))
        return redirect('certificate_type_list')
    
    if request.method == 'POST':
        certificate_type.delete()
        messages.success(request, _('Đã xóa loại chứng chỉ thành công.'))
        return redirect('certificate_type_list')
    
    context = {
        'certificate_type': certificate_type
    }
    
    return render(request, 'employee/certificate_type_confirm_delete.html', context)

# Department management
@login_required
@check_module_permission('organization', 'View')
def department_list(request):
    """List all departments"""
    departments = Department.objects.all().order_by('department_name')
    
    # Get employee count for each department
    for dept in departments:
        dept.employee_count = Employee.objects.filter(department=dept, status='Working').count()
    
    context = {
        'departments': departments
    }
    
    return render(request, 'employee/department_list.html', context)

@login_required
@check_module_permission('organization', 'View')
def department_detail(request, pk):
    """View department details and employees"""
    department = get_object_or_404(Department, pk=pk)
    employees = Employee.objects.filter(department=department).order_by('full_name')
    
    # Group employees by position
    positions = {}
    for employee in employees:
        position_name = employee.position.position_name if employee.position else _('No Position')
        if position_name not in positions:
            positions[position_name] = []
        positions[position_name].append(employee)
    
    context = {
        'department': department,
        'employees': employees,
        'positions': positions,
        'employee_count': employees.count(),
        'active_count': employees.filter(status='Working').count()
    }
    
    return render(request, 'employee/department_detail.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def department_create(request):
    """Create a new department"""
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        
        if form.is_valid():
            department = form.save()
            messages.success(request, _('Đã tạo phòng ban thành công.'))
            return redirect('department_list')
    else:
        form = DepartmentForm()
    
    context = {
        'form': form,
        'title': _('Create Department')
    }
    
    return render(request, 'employee/department_form.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def department_update(request, pk):
    """Update an existing department"""
    department = get_object_or_404(Department, pk=pk)
    
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        
        if form.is_valid():
            form.save()
            messages.success(request, _('Đã cập nhật phòng ban thành công.'))
            return redirect('department_list')
    else:
        form = DepartmentForm(instance=department)
    
    context = {
        'form': form,
        'department': department,
        'title': _('Update Department')
    }
    
    return render(request, 'employee/department_form.html', context)

@login_required
@check_module_permission('organization', 'Delete')
def department_delete(request, pk):
    """Delete a department"""
    department = get_object_or_404(Department, pk=pk)
    
    # Check if department has employees
    if Employee.objects.filter(department=department).exists():
        messages.error(request, _('Không thể xóa phòng ban có nhân viên.'))
        return redirect('department_list')
    
    if request.method == 'POST':
        department.delete()
        messages.success(request, _('Đã xóa phòng ban thành công.'))
        return redirect('department_list')
    
    context = {
        'department': department
    }
    
    return render(request, 'employee/department_confirm_delete.html', context)

# Position management
@login_required
@check_module_permission('organization', 'View')
def position_list(request):
    """List all positions"""
    positions = Position.objects.all().order_by('position_name')
    
    # Get employee count for each position
    for pos in positions:
        pos.employee_count = Employee.objects.filter(position=pos, status='Working').count()
    
    context = {
        'positions': positions
    }
    
    return render(request, 'employee/position_list.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def position_create(request):
    """Create a new position"""
    if request.method == 'POST':
        form = PositionForm(request.POST)
        
        if form.is_valid():
            position = form.save()
            messages.success(request, _('Đã tạo vị trí công việc thành công.'))
            return redirect('position_list')
    else:
        form = PositionForm()
    
    context = {
        'form': form,
        'title': _('Create Position')
    }
    
    return render(request, 'employee/position_form.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def position_update(request, pk):
    """Update an existing position"""
    position = get_object_or_404(Position, pk=pk)
    
    if request.method == 'POST':
        form = PositionForm(request.POST, instance=position)
        
        if form.is_valid():
            form.save()
            messages.success(request, _('Đã cập nhật vị trí công việc thành công.'))
            return redirect('position_list')
    else:
        form = PositionForm(instance=position)
    
    context = {
        'form': form,
        'position': position,
        'title': _('Update Position')
    }
    
    return render(request, 'employee/position_form.html', context)

@login_required
@check_module_permission('organization', 'Delete')
def position_delete(request, pk):
    """Delete a position"""
    position = get_object_or_404(Position, pk=pk)
    
    # Check if position has employees
    if Employee.objects.filter(position=position).exists():
        messages.error(request, _('Không thể xóa vị trí công việc có nhân viên.'))
        return redirect('position_list')
    
    if request.method == 'POST':
        position.delete()
        messages.success(request, _('Đã xóa vị trí công việc thành công.'))
        return redirect('position_list')
    
    context = {
        'position': position
    }
    
    return render(request, 'employee/position_confirm_delete.html', context)

# Education level management
@login_required
@check_module_permission('organization', 'View')
def education_list(request):
    """List all education levels"""
    education_levels = EducationLevel.objects.all().order_by('education_name')
    
    # Get employee count for each education level
    for edu in education_levels:
        edu.employee_count = Employee.objects.filter(education=edu, status='Working').count()
    
    context = {
        'education_levels': education_levels
    }
    
    return render(request, 'employee/education_list.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def education_create(request):
    """Create a new education level"""
    if request.method == 'POST':
        form = EducationLevelForm(request.POST)
        
        if form.is_valid():
            education = form.save()
            messages.success(request, _('Đã tạo cấp độ học vấn thành công.'))
            return redirect('education_list')
    else:
        form = EducationLevelForm()
    
    context = {
        'form': form,
        'title': _('Create Education Level')
    }
    
    return render(request, 'employee/education_form.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def education_update(request, pk):
    """Update an existing education level"""
    education = get_object_or_404(EducationLevel, pk=pk)
    
    if request.method == 'POST':
        form = EducationLevelForm(request.POST, instance=education)
        
        if form.is_valid():
            form.save()
            messages.success(request, _('Đã cập nhật cấp độ học vấn thành công.'))
            return redirect('education_list')
    else:
        form = EducationLevelForm(instance=education)
    
    context = {
        'form': form,
        'education': education,
        'title': _('Update Education Level')
    }
    
    return render(request, 'employee/education_form.html', context)

@login_required
@check_module_permission('organization', 'Delete')
def education_delete(request, pk):
    """Delete an education level"""
    education = get_object_or_404(EducationLevel, pk=pk)
    
    # Check if education level has employees
    if Employee.objects.filter(education=education).exists():
        messages.error(request, _('Không thể xóa cấp độ học vấn có nhân viên.'))
        return redirect('education_list')
    
    if request.method == 'POST':
        education.delete()
        messages.success(request, _('Đã xóa cấp độ học vấn thành công.'))
        return redirect('education_list')
    
    context = {
        'education': education
    }
    
    return render(request, 'employee/education_confirm_delete.html', context)

# Academic title management
@login_required
@check_module_permission('organization', 'View')
def title_list(request):
    """List all academic titles"""
    titles = AcademicTitle.objects.all().order_by('title_name')
    
    # Get employee count for each title
    for title in titles:
        title.employee_count = Employee.objects.filter(title=title, status='Working').count()
    
    context = {
        'titles': titles
    }
    
    return render(request, 'employee/title_list.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def title_create(request):
    """Create a new academic title"""
    if request.method == 'POST':
        form = AcademicTitleForm(request.POST)
        
        if form.is_valid():
            title = form.save()
            messages.success(request, _('Đã tạo học hàm học vị thành công.'))
            return redirect('title_list')
    else:
        form = AcademicTitleForm()
    
    context = {
        'form': form,
        'title_text': _('Create Academic Title')
    }
    
    return render(request, 'employee/title_form.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def title_update(request, pk):
    """Update an existing academic title"""
    title = get_object_or_404(AcademicTitle, pk=pk)
    
    if request.method == 'POST':
        form = AcademicTitleForm(request.POST, instance=title)
        
        if form.is_valid():
            form.save()
            messages.success(request, _('Đã cập nhật học hàm học vị thành công.'))
            return redirect('title_list')
    else:
        form = AcademicTitleForm(instance=title)
    
    context = {
        'form': form,
        'academic_title': title,
        'title_text': _('Update Academic Title')
    }
    
    return render(request, 'employee/title_form.html', context)

@login_required
@check_module_permission('organization', 'Delete')
def title_delete(request, pk):
    """Delete an academic title"""
    title = get_object_or_404(AcademicTitle, pk=pk)
    
    # Check if title has employees
    if Employee.objects.filter(title=title).exists():
        messages.error(request, _('Không thể xóa học hàm học vị có nhân viên.'))
        return redirect('title_list')
    
    if request.method == 'POST':
        title.delete()
        messages.success(request, _('Đã xóa học hàm học vị thành công.'))
        return redirect('title_list')
    
    context = {
        'academic_title': title
    }
    
    return render(request, 'employee/title_confirm_delete.html', context)

# Import/Export functionality
@login_required
@hr_required
def export_employees(request):
    """Export employees as CSV or Excel"""
    format_type = request.GET.get('format', 'csv')
    
    # Apply filters from request if any
    query = request.GET.get('q', '')
    department_filter = request.GET.get('department', '')
    status_filter = request.GET.get('status', '')
    
    employees = Employee.objects.select_related('department', 'position', 'education', 'title').all()
    
    if query:
        employees = employees.filter(
            Q(full_name__icontains=query) |
            Q(email__icontains=query) |
            Q(id_card__icontains=query) |
            Q(phone__icontains=query)
        )
    
    if department_filter:
        employees = employees.filter(department_id=department_filter)
    
    if status_filter:
        employees = employees.filter(status=status_filter)
    
    # Define fields to export
    fields = [
        {'field': 'employee_id', 'display': _('ID')},
        {'field': 'full_name', 'display': _('Full Name')},
        {'field': 'email', 'display': _('Email')},
        {'field': 'phone', 'display': _('Phone')},
        {'field': 'date_of_birth', 'display': _('Date of Birth')},
        {'field': 'gender', 'display': _('Gender')},
        {'field': 'department.department_name', 'display': _('Department')},
        {'field': 'position.position_name', 'display': _('Position')},
        {'field': 'hire_date', 'display': _('Hire Date')},
        {'field': 'id_card', 'display': _('ID Card')},
        {'field': 'address', 'display': _('Address')},
        {'field': 'status', 'display': _('Status')}
    ]
    
    file_name = f"employees_export_{datetime.now().strftime('%Y%m%d')}"
    
    if format_type == 'excel':
        return ExportHelper.export_as_excel(employees, fields, file_name)
    else:
        return ExportHelper.export_as_csv(employees, fields, file_name)

@login_required
@hr_required
def import_employees(request):
    """Import employees from CSV"""
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, _('Vui lòng tải lên tệp CSV'))
            return redirect('employee_list')
        
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            success_count = 0
            error_count = 0
            errors = []
            
            for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header row
                try:
                    email = row.get('Email', '').strip()
                    full_name = row.get('Full Name', '').strip()
                    
                    if not email or not full_name:
                        error_count += 1
                        errors.append(f"Dòng {row_num}: Thiếu trường bắt buộc (Email hoặc Họ tên)")
                        continue
                    
                    # Check if employee already exists
                    if Employee.objects.filter(email=email).exists():
                        employee = Employee.objects.get(email=email)
                        # Update existing employee
                        employee.full_name = full_name
                        employee.phone = row.get('Phone', '').strip()
                        
                        # Update other fields if provided
                        if row.get('Date of Birth'):
                            try:
                                employee.date_of_birth = datetime.strptime(row.get('Date of Birth'), '%Y-%m-%d').date()
                            except ValueError:
                                pass
                        
                        if row.get('Gender'):
                            gender = row.get('Gender').strip()
                            if gender in ['Male', 'Female', 'Other']:
                                employee.gender = gender
                        
                        if row.get('Department'):
                            dept_name = row.get('Department').strip()
                            dept = Department.objects.filter(department_name=dept_name).first()
                            if dept:
                                employee.department = dept
                        
                        if row.get('Position'):
                            pos_name = row.get('Position').strip()
                            pos = Position.objects.filter(position_name=pos_name).first()
                            if pos:
                                employee.position = pos
                        
                        if row.get('Hire Date'):
                            try:
                                employee.hire_date = datetime.strptime(row.get('Hire Date'), '%Y-%m-%d').date()
                            except ValueError:
                                pass
                        
                        employee.save()
                    else:
                        # Create new employee
                        employee = Employee(
                            full_name=full_name,
                            email=email,
                            phone=row.get('Phone', '').strip()
                        )
                        
                        # Set other fields if provided
                        if row.get('Date of Birth'):
                            try:
                                employee.date_of_birth = datetime.strptime(row.get('Date of Birth'), '%Y-%m-%d').date()
                            except ValueError:
                                pass
                        
                        if row.get('Gender'):
                            gender = row.get('Gender').strip()
                            if gender in ['Male', 'Female', 'Other']:
                                employee.gender = gender
                        
                        if row.get('Department'):
                            dept_name = row.get('Department').strip()
                            dept = Department.objects.filter(department_name=dept_name).first()
                            if dept:
                                employee.department = dept
                        
                        if row.get('Position'):
                            pos_name = row.get('Position').strip()
                            pos = Position.objects.filter(position_name=pos_name).first()
                            if pos:
                                employee.position = pos
                        
                        if row.get('Hire Date'):
                            try:
                                employee.hire_date = datetime.strptime(row.get('Hire Date'), '%Y-%m-%d').date()
                            except ValueError:
                                pass
                        
                        employee.save()
                    
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append(f"Dòng {row_num}: {str(e)}")
            
            if error_count:
                messages.warning(request, _(f'Đã nhập {success_count} nhân viên với {error_count} lỗi.'))
            else:
                messages.success(request, _(f'Đã nhập thành công {success_count} nhân viên.'))
            
            if errors:
                request.session['import_errors'] = errors
                return redirect('import_errors')
            
            return redirect('employee_list')
            
        except Exception as e:
            messages.error(request, _(f'Lỗi xử lý tệp CSV: {str(e)}'))
    
    # Get sample CSV content
    sample_csv = "Full Name,Email,Phone,Date of Birth,Gender,Department,Position,Hire Date\n"
    sample_csv += "John Doe,john.doe@example.com,1234567890,1990-01-01,Male,IT,Developer,2020-01-15\n"
    sample_csv += "Jane Smith,jane.smith@example.com,9876543210,1992-05-20,Female,HR,Manager,2019-11-10"
    
    context = {
        'sample_csv': sample_csv
    }
    
    return render(request, 'employee/import_employees.html', context)

@login_required
@hr_required
def import_errors(request):
    """Display errors from import process"""
    errors = request.session.get('import_errors', [])
    
    if not errors:
        return redirect('employee_list')
    
    # Clear the session
    if 'import_errors' in request.session:
        del request.session['import_errors']
    
    context = {
        'errors': errors
    }
    
    return render(request, 'employee/import_errors.html', context)

@login_required
@admin_required
def pending_approval_list(request):
    """List all employees with pending approval status"""
    employees = Employee.objects.filter(approval_status='Pending').order_by('-created_date')
    
    # Search functionality
    query = request.GET.get('q', '')
    if query:
        employees = employees.filter(
            Q(full_name__icontains=query) |
            Q(email__icontains=query) |
            Q(id_card__icontains=query) |
            Q(phone__icontains=query)
        )
    
    # Department filter
    department_filter = request.GET.get('department', '')
    if department_filter:
        employees = employees.filter(department_id=department_filter)
    
    # Paginate the results
    paginator = Paginator(employees, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get list of departments for filter dropdown
    departments = Department.objects.filter(status=1).order_by('department_name')
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'departments': departments,
        'department_filter': department_filter,
        'total_count': employees.count(),
    }
    
    return render(request, 'employee/pending_approval_list.html', context)
