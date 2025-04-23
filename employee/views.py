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
from accounts.models import User, SystemLog

# -----------------------------------------------------------------------------
# QUẢN LÝ NHÂN VIÊN
# -----------------------------------------------------------------------------

@login_required
@check_module_permission('employee', 'View')
def employee_list(request):
    """Danh sách tất cả nhân viên với bộ lọc"""
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
    
    # Sắp xếp theo tên
    employees = employees.order_by('full_name')
    
    # Tính tổng cho tóm tắt
    total_count = employees.count()
    active_count = employees.filter(status='Working').count()
    inactive_count = total_count - active_count
    
    # Phân trang kết quả
    paginator = Paginator(employees, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Lấy danh sách phòng ban và vị trí cho bộ lọc dropdown
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
    """Xem chi tiết nhân viên"""
    employee = get_object_or_404(Employee, pk=pk)
    
    # Lấy thông tin liên quan
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
    }
    
    return render(request, 'employee/employee_detail.html', context)

@login_required
@check_module_permission('employee', 'Edit')
def employee_create(request):
    """Tạo nhân viên mới"""
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        location_form = EmployeeLocationForm(request.POST)
        
        if form.is_valid() and location_form.is_valid():
            employee = form.save(commit=False)
            
            # Tự động chấp thuận cho Admin, HR và Manager
            if hasattr(employee, 'user') and employee.user and employee.user.role in ['Admin', 'HR', 'Manager']:
                employee.approval_status = 'Approved'
                employee.approval_date = timezone.now()
            
            employee.save()
            
            # Lưu thông tin vị trí
            location = location_form.save(commit=False)
            location.employee = employee
            location.save()
            
            # Xử lý tải lên tài liệu
            process_document_uploads(request, employee)
            
            messages.success(request, 'Tạo nhân viên thành công.')
            return redirect('employee_detail', pk=employee.pk)
    else:
        form = EmployeeForm()
        location_form = EmployeeLocationForm()
    
    context = {
        'form': form,
        'location_form': location_form,
        'is_create': True,
        'title': 'Tạo mới nhân viên'
    }
    
    return render(request, 'employee/employee_form.html', context)

def process_document_uploads(request, employee):
    """Xử lý tải lên tài liệu cho nhân viên"""
    document_fields = {
        'id_card_front': 'Mặt trước CMND/CCCD',
        'id_card_back': 'Mặt sau CMND/CCCD',
        'diploma': 'Bằng cấp/Chứng chỉ',
        'other_documents': 'Tài liệu khác'
    }
    
    for field_name, doc_type in document_fields.items():
        if field_name in request.FILES:
            uploaded_file = request.FILES[field_name]
            
            # Tạo bản ghi tài liệu
            document = EmployeeDocument(
                employee=employee,
                document_type=field_name,
                file=uploaded_file,
                file_name=uploaded_file.name,
                file_type=uploaded_file.content_type,
                file_size=uploaded_file.size // 1024  # Chuyển đổi byte sang KB
            )
            document.save()
            
            # Ghi log việc tải lên tài liệu
            if hasattr(request, 'user') and request.user.is_authenticated:
                SystemLog.objects.create(
                    user=request.user,
                    action="Tải lên tài liệu",
                    object_type="EmployeeDocument",
                    object_id=document.document_id,
                    details=f"Đã tải lên {doc_type} cho {employee.full_name}"
                )

@login_required
@admin_required
def employee_approve(request, pk):
    """Phê duyệt hoặc từ chối một nhân viên đang chờ duyệt"""
    employee = get_object_or_404(Employee, pk=pk)
    
    if employee.approval_status != 'Pending':
        messages.warning(request, 'Nhân viên này không trong trạng thái chờ phê duyệt.')
        return redirect('employee_detail', pk=pk)
    
    if request.method == 'POST':
        approval_action = request.POST.get('approval_action')
        notes = request.POST.get('notes', '')
        
        if approval_action == 'approve':
            # Cập nhật trạng thái nhân viên
            employee.approval_status = 'Approved'
            employee.approval_date = timezone.now()
            employee.approval_notes = notes
            employee.save()
            
            # Gửi email thông báo phê duyệt
            send_approval_email(employee, approved=True)
            
            # Tạo thông báo cho nhân viên nếu họ có tài khoản người dùng
            try:
                user = User.objects.get(email=employee.email)
                create_notification(
                    user=user,
                    notification_type='Success',
                    title='Hồ sơ nhân viên đã được phê duyệt',
                    message='Hồ sơ nhân viên của bạn đã được phê duyệt. Bạn có thể truy cập hệ thống ngay bây giờ.',
                    link=reverse('employee_dashboard')
                )
            except User.DoesNotExist:
                pass
            
            messages.success(request, 'Nhân viên đã được phê duyệt thành công.')
            
        elif approval_action == 'reject':
            # Cập nhật trạng thái nhân viên
            employee.approval_status = 'Rejected'
            employee.approval_date = timezone.now()
            employee.approval_notes = notes
            employee.save()
            
            # Gửi email từ chối
            send_approval_email(employee, approved=False)
            
            messages.warning(request, 'Nhân viên đã bị từ chối.')
        
        return redirect('employee_detail', pk=pk)
    
    return render(request, 'employee/employee_approve.html', {'employee': employee})

def send_approval_email(employee, approved=True):
    """Gửi email phê duyệt/từ chối nhân viên"""
    if not employee.email:
        return
    
    if approved:
        subject = 'Hồ sơ nhân viên của bạn đã được phê duyệt'
        template = 'employee_approved'
    else:
        subject = 'Hồ sơ nhân viên của bạn cần được chỉnh sửa'
        template = 'employee_rejected'
    
    # Sử dụng dịch vụ gửi tin nhắn nếu có
    try:
        # Lấy năm hiện tại cho footer
        current_year = timezone.now().year
        
        # Sử dụng dịch vụ email dựa trên mẫu
        EmailService.send_email_by_template(
            template_code=template,
            to_email=employee.email,
            context_dict={
                'name': employee.full_name,
                'notes': employee.approval_notes or 'Không có ghi chú bổ sung',
                'approval_date': employee.approval_date,
                'login_url': settings.SITE_URL + reverse('login'),
                'company_name': settings.COMPANY_NAME,
                'current_year': current_year
            }
        )
    except Exception as e:
        # Sử dụng email đơn giản dự phòng
        from django.core.mail import send_mail
        
        message = f"Kính gửi {employee.full_name},\n\n"
        
        if approved:
            message += "Chúng tôi vui mừng thông báo rằng hồ sơ nhân viên của bạn đã được phê duyệt. Bạn có thể đăng nhập vào hệ thống bằng thông tin đăng nhập của mình.\n\n"
        else:
            message += "Chúng tôi rất tiếc phải thông báo rằng hồ sơ nhân viên của bạn chưa được phê duyệt tại thời điểm này. Vui lòng xem bên dưới để biết thêm thông tin.\n\n"
        
        if employee.approval_notes:
            message += f"Ghi chú: {employee.approval_notes}\n\n"
        
        message += "Trân trọng,\nPhòng Nhân sự"
        
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
    """Cập nhật thông tin nhân viên"""
    employee = get_object_or_404(Employee, pk=pk)
    
    # Lấy vị trí nếu tồn tại hoặc chuẩn bị tạo mới
    try:
        location = EmployeeLocation.objects.get(employee=employee)
    except EmployeeLocation.DoesNotExist:
        location = None
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        location_form = EmployeeLocationForm(request.POST, instance=location)
        
        if form.is_valid() and location_form.is_valid():
            # Lưu nhân viên
            employee = form.save()
            
            # Lưu hoặc tạo vị trí
            if location:
                location_form.save()
            else:
                location = location_form.save(commit=False)
                location.employee = employee
                location.save()
            
            messages.success(request, 'Cập nhật nhân viên thành công.')
            return redirect('employee_detail', pk=employee.pk)
    else:
        form = EmployeeForm(instance=employee)
        location_form = EmployeeLocationForm(instance=location)
    
    context = {
        'form': form,
        'location_form': location_form,
        'is_create': False,
        'employee': employee,
        'title': 'Cập nhật nhân viên'
    }
    
    return render(request, 'employee/employee_form.html', context)

@login_required
@check_module_permission('employee', 'Delete')
def employee_delete(request, pk):
    """Xóa nhân viên"""
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        employee_name = employee.full_name
        employee.delete()
        messages.success(request, f'Đã xóa nhân viên "{employee_name}" thành công.')
        return redirect('employee_list')
    
    return render(request, 'employee/employee_confirm_delete.html', {'employee': employee})

@login_required
@admin_required
def pending_approval_list(request):
    """Danh sách tất cả nhân viên có trạng thái chờ phê duyệt"""
    employees = Employee.objects.filter(approval_status='Pending').order_by('-created_date')
    
    # Chức năng tìm kiếm
    query = request.GET.get('q', '')
    if query:
        employees = employees.filter(
            Q(full_name__icontains=query) |
            Q(email__icontains=query) |
            Q(id_card__icontains=query) |
            Q(phone__icontains=query)
        )
    
    # Bộ lọc phòng ban
    department_filter = request.GET.get('department', '')
    if department_filter:
        employees = employees.filter(department_id=department_filter)
    
    # Phân trang kết quả
    paginator = Paginator(employees, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Lấy danh sách phòng ban cho bộ lọc dropdown
    departments = Department.objects.filter(status=1).order_by('department_name')
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'departments': departments,
        'department_filter': department_filter,
        'total_count': employees.count(),
    }
    
    return render(request, 'employee/pending_approval_list.html', context)

# -----------------------------------------------------------------------------
# QUẢN LÝ VỊ TRÍ
# -----------------------------------------------------------------------------

@login_required
@check_module_permission('employee', 'View')
def employee_location(request, employee_id):
    """Xem chi tiết vị trí của nhân viên"""
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
    """Cập nhật vị trí của nhân viên"""
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
            
            messages.success(request, 'Thông tin vị trí đã được cập nhật thành công.')
            return redirect('employee_detail', pk=employee_id)
    else:
        form = EmployeeLocationForm(instance=location)
    
    context = {
        'form': form,
        'employee': employee,
        'location': location,
        'title': 'Cập nhật thông tin vị trí'
    }
    
    return render(request, 'employee/location_form.html', context)

# -----------------------------------------------------------------------------
# QUẢN LÝ BẢO HIỂM VÀ THUẾ
# -----------------------------------------------------------------------------

@login_required
@check_module_permission('employee', 'View')
def insurance_tax_detail(request, employee_id):
    """Xem chi tiết bảo hiểm và thuế cho nhân viên"""
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
    """Tạo thông tin bảo hiểm và thuế"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    # Kiểm tra nếu bản ghi đã tồn tại
    if InsuranceAndTax.objects.filter(employee=employee).exists():
        messages.warning(request, 'Thông tin bảo hiểm và thuế cho nhân viên này đã tồn tại')
        return redirect('insurance_tax_update', employee_id=employee_id)
    
    if request.method == 'POST':
        form = InsuranceAndTaxForm(request.POST)
        
        if form.is_valid():
            insurance = form.save(commit=False)
            insurance.employee = employee
            insurance.save()
            
            messages.success(request, 'Đã tạo thông tin bảo hiểm và thuế thành công.')
            return redirect('employee_detail', pk=employee_id)
    else:
        form = InsuranceAndTaxForm()
    
    context = {
        'form': form,
        'employee': employee,
        'is_create': True,
        'title': 'Tạo thông tin bảo hiểm & thuế'
    }
    
    return render(request, 'employee/insurance_tax_form.html', context)

@login_required
@check_module_permission('employee', 'Edit')
def insurance_tax_update(request, employee_id):
    """Cập nhật thông tin bảo hiểm và thuế"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    try:
        insurance = InsuranceAndTax.objects.get(employee=employee)
    except InsuranceAndTax.DoesNotExist:
        return redirect('insurance_tax_create', employee_id=employee_id)
    
    if request.method == 'POST':
        form = InsuranceAndTaxForm(request.POST, instance=insurance)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật thông tin bảo hiểm và thuế thành công.')
            return redirect('employee_detail', pk=employee_id)
    else:
        form = InsuranceAndTaxForm(instance=insurance)
    
    context = {
        'form': form,
        'employee': employee,
        'is_create': False,
        'title': 'Cập nhật thông tin bảo hiểm & thuế'
    }
    
    return render(request, 'employee/insurance_tax_form.html', context)

# -----------------------------------------------------------------------------
# QUẢN LÝ CHỨNG CHỈ
# -----------------------------------------------------------------------------

@login_required
@check_module_permission('employee', 'View')
def employee_certificates(request, employee_id):
    """Xem tất cả chứng chỉ của nhân viên"""
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
    """Thêm chứng chỉ mới cho nhân viên"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    if request.method == 'POST':
        form = EmployeeCertificateForm(request.POST, request.FILES)
        
        if form.is_valid():
            certificate = form.save(commit=False)
            certificate.employee = employee
            
            # Tự động xác định trạng thái dựa trên ngày hết hạn
            if certificate.expiry_date:
                if certificate.expiry_date < date.today():
                    certificate.status = 'Expired'
                else:
                    certificate.status = 'Valid'
            
            certificate.save()
            messages.success(request, 'Đã thêm chứng chỉ thành công.')
            return redirect('employee_certificates', employee_id=employee_id)
    else:
        form = EmployeeCertificateForm()
    
    context = {
        'form': form,
        'employee': employee,
        'title': 'Thêm chứng chỉ'
    }
    
    return render(request, 'employee/certificate_form.html', context)

@login_required
@check_module_permission('employee', 'Edit')
def edit_certificate(request, certificate_id):
    """Chỉnh sửa chứng chỉ hiện có"""
    certificate = get_object_or_404(EmployeeCertificate, pk=certificate_id)
    employee = certificate.employee
    
    if request.method == 'POST':
        form = EmployeeCertificateForm(request.POST, request.FILES, instance=certificate)
        
        if form.is_valid():
            certificate = form.save(commit=False)
            
            # Tự động xác định trạng thái dựa trên ngày hết hạn nếu không bị thu hồi
            if certificate.status != 'Revoked' and certificate.expiry_date:
                if certificate.expiry_date < date.today():
                    certificate.status = 'Expired'
                else:
                    certificate.status = 'Valid'
            
            certificate.save()
            messages.success(request, 'Đã cập nhật chứng chỉ thành công.')
            return redirect('employee_certificates', employee_id=employee.pk)
    else:
        form = EmployeeCertificateForm(instance=certificate)
    
    context = {
        'form': form,
        'employee': employee,
        'certificate': certificate,
        'title': 'Chỉnh sửa chứng chỉ'
    }
    
    return render(request, 'employee/certificate_form.html', context)

@login_required
@check_module_permission('employee', 'Delete')
def delete_certificate(request, certificate_id):
    """Xóa chứng chỉ"""
    certificate = get_object_or_404(EmployeeCertificate, pk=certificate_id)
    employee_id = certificate.employee.pk
    
    if request.method == 'POST':
        certificate.delete()
        messages.success(request, 'Đã xóa chứng chỉ thành công.')
        return redirect('employee_certificates', employee_id=employee_id)
    
    context = {
        'certificate': certificate,
        'employee': certificate.employee
    }
    
    return render(request, 'employee/certificate_confirm_delete.html', context)

@login_required
def my_certificates(request):
    """Xem chứng chỉ của người dùng hiện tại"""
    if not hasattr(request.user, 'employee') or not request.user.employee:
        messages.error(request, 'Bạn không có hồ sơ nhân viên.')
        return redirect('dashboard')
    
    certificates = EmployeeCertificate.objects.filter(
        employee=request.user.employee
    ).order_by('-issued_date')
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        certificates = certificates.filter(status=status_filter)
    
    # Kiểm tra chứng chỉ sắp hết hạn
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
    """Thêm chứng chỉ cho người dùng hiện tại"""
    if not hasattr(request.user, 'employee') or not request.user.employee:
        messages.error(request, 'Bạn không có hồ sơ nhân viên.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = EmployeeCertificateForm(request.POST, request.FILES)
        
        if form.is_valid():
            certificate = form.save(commit=False)
            certificate.employee = request.user.employee
            
            # Tự động xác định trạng thái dựa trên ngày hết hạn
            if certificate.expiry_date:
                if certificate.expiry_date < date.today():
                    certificate.status = 'Expired'
                else:
                    certificate.status = 'Valid'
            
            certificate.save()
            
            # Thông báo cho HR về chứng chỉ mới
            create_notification(
                role='HR',
                notification_type='Certificate',
                title='Đã thêm chứng chỉ mới',
                message=f"{request.user.employee.full_name} đã thêm một chứng chỉ mới: {certificate.certificate_name}",
                link=reverse('edit_certificate', args=[certificate.certificate_id])
            )
            
            messages.success(request, 'Đã thêm chứng chỉ thành công.')
            return redirect('my_certificates')
    else:
        form = EmployeeCertificateForm()
    
    context = {
        'form': form,
        'title': 'Thêm chứng chỉ của tôi'
    }
    
    return render(request, 'employee/certificate_form.html', context)

# -----------------------------------------------------------------------------
# QUẢN LÝ LOẠI CHỨNG CHỈ
# -----------------------------------------------------------------------------

@login_required
@hr_required
def certificate_type_list(request):
    """Danh sách tất cả loại chứng chỉ"""
    certificate_types = CertificateType.objects.all().order_by('type_name')
    
    context = {
        'certificate_types': certificate_types
    }
    
    return render(request, 'employee/certificate_type_list.html', context)

@login_required
@hr_required
def certificate_type_create(request):
    """Tạo loại chứng chỉ mới"""
    if request.method == 'POST':
        form = CertificateTypeForm(request.POST)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã tạo loại chứng chỉ thành công.')
            return redirect('certificate_type_list')
    else:
        form = CertificateTypeForm()
    
    context = {
        'form': form,
        'title': 'Tạo loại chứng chỉ'
    }
    
    return render(request, 'employee/certificate_type_form.html', context)

@login_required
@hr_required
def certificate_type_update(request, pk):
    """Cập nhật loại chứng chỉ hiện có"""
    certificate_type = get_object_or_404(CertificateType, pk=pk)
    
    if request.method == 'POST':
        form = CertificateTypeForm(request.POST, instance=certificate_type)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật loại chứng chỉ thành công.')
            return redirect('certificate_type_list')
    else:
        form = CertificateTypeForm(instance=certificate_type)
    
    context = {
        'form': form,
        'certificate_type': certificate_type,
        'title': 'Cập nhật loại chứng chỉ'
    }
    
    return render(request, 'employee/certificate_type_form.html', context)

@login_required
@hr_required
def certificate_type_delete(request, pk):
    """Xóa loại chứng chỉ"""
    certificate_type = get_object_or_404(CertificateType, pk=pk)
    
    # Kiểm tra xem loại chứng chỉ có đang được sử dụng không
    if EmployeeCertificate.objects.filter(type=certificate_type).exists():
        messages.error(request, 'Không thể xóa loại chứng chỉ đang được sử dụng.')
        return redirect('certificate_type_list')
    
    if request.method == 'POST':
        certificate_type.delete()
        messages.success(request, 'Đã xóa loại chứng chỉ thành công.')
        return redirect('certificate_type_list')
    
    context = {
        'certificate_type': certificate_type
    }
    
    return render(request, 'employee/certificate_type_confirm_delete.html', context)

# -----------------------------------------------------------------------------
# QUẢN LÝ PHÒNG BAN
# -----------------------------------------------------------------------------

@login_required
@check_module_permission('organization', 'View')
def department_list(request):
    """Danh sách tất cả phòng ban"""
    departments = Department.objects.all().order_by('department_name')
    
    # Lấy số lượng nhân viên cho mỗi phòng ban
    for dept in departments:
        dept.employee_count = Employee.objects.filter(department=dept, status='Working').count()
    
    context = {
        'departments': departments
    }
    
    return render(request, 'employee/department/department_list.html', context)

@login_required
@check_module_permission('organization', 'View')
def department_detail(request, pk):
    """Xem chi tiết phòng ban và nhân viên"""
    department = get_object_or_404(Department, pk=pk)
    employees = Employee.objects.filter(department=department).order_by('full_name')
    
    # Nhóm nhân viên theo vị trí
    positions = {}
    for employee in employees:
        position_name = employee.position.position_name if employee.position else 'Không có vị trí'
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
    
    return render(request, 'employee/department/department_detail.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def department_create(request):
    """Tạo phòng ban mới"""
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        
        if form.is_valid():
            department = form.save()
            messages.success(request, 'Đã tạo phòng ban thành công.')
            return redirect('department_list')
    else:
        form = DepartmentForm()
    
    context = {
        'form': form,
        'title': 'Tạo phòng ban'
    }
    
    return render(request, 'employee/department/department_form.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def department_update(request, pk):
    """Cập nhật phòng ban hiện có"""
    department = get_object_or_404(Department, pk=pk)
    
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật phòng ban thành công.')
            return redirect('department_list')
    else:
        form = DepartmentForm(instance=department)
    
    context = {
        'form': form,
        'department': department,
        'title': 'Cập nhật phòng ban'
    }
    
    return render(request, 'employee/department/department_form.html', context)

@login_required
@check_module_permission('organization', 'Delete')
def department_delete(request, pk):
    """Xóa phòng ban"""
    department = get_object_or_404(Department, pk=pk)
    
    # Kiểm tra xem phòng ban có nhân viên không
    if Employee.objects.filter(department=department).exists():
        messages.error(request, 'Không thể xóa phòng ban có nhân viên.')
        return redirect('department_list')
    
    if request.method == 'POST':
        department.delete()
        messages.success(request, 'Đã xóa phòng ban thành công.')
        return redirect('department_list')
    
    context = {
        'department': department
    }
    
    return render(request, 'employee/department/department_confirm_delete.html', context)

# -----------------------------------------------------------------------------
# QUẢN LÝ VỊ TRÍ CÔNG VIỆC
# -----------------------------------------------------------------------------

@login_required
@check_module_permission('organization', 'View')
def position_list(request):
    """Danh sách tất cả vị trí công việc"""
    positions = Position.objects.all().order_by('position_name')
    
    # Lấy số lượng nhân viên cho mỗi vị trí
    for pos in positions:
        pos.employee_count = Employee.objects.filter(position=pos, status='Working').count()
    
    context = {
        'positions': positions
    }
    
    return render(request, 'employee/position/position_list.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def position_create(request):
    """Tạo vị trí công việc mới"""
    if request.method == 'POST':
        form = PositionForm(request.POST)
        
        if form.is_valid():
            position = form.save()
            messages.success(request, 'Đã tạo vị trí công việc thành công.')
            return redirect('position_list')
    else:
        form = PositionForm()
    
    context = {
        'form': form,
        'title': 'Tạo vị trí công việc'
    }
    
    return render(request, 'employee/position/position_form.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def position_update(request, pk):
    """Cập nhật vị trí công việc hiện có"""
    position = get_object_or_404(Position, pk=pk)
    
    if request.method == 'POST':
        form = PositionForm(request.POST, instance=position)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật vị trí công việc thành công.')
            return redirect('position_list')
    else:
        form = PositionForm(instance=position)
    
    context = {
        'form': form,
        'position': position,
        'title': 'Cập nhật vị trí công việc'
    }
    
    return render(request, 'employee/position/position_form.html', context)

@login_required
@check_module_permission('organization', 'Delete')
def position_delete(request, pk):
    """Xóa vị trí công việc"""
    position = get_object_or_404(Position, pk=pk)
    
    # Kiểm tra xem vị trí có nhân viên không
    if Employee.objects.filter(position=position).exists():
        messages.error(request, 'Không thể xóa vị trí công việc có nhân viên.')
        return redirect('position_list')
    
    if request.method == 'POST':
        position.delete()
        messages.success(request, 'Đã xóa vị trí công việc thành công.')
        return redirect('position_list')
    
    context = {
        'position': position
    }
    
    return render(request, 'employee/position/position_confirm_delete.html', context)

# -----------------------------------------------------------------------------
# QUẢN LÝ TRÌNH ĐỘ HỌC VẤN
# -----------------------------------------------------------------------------

@login_required
@check_module_permission('organization', 'View')
def education_list(request):
    """Danh sách tất cả trình độ học vấn"""
    education_levels = EducationLevel.objects.all().order_by('education_name')
    
    # Lấy số lượng nhân viên cho mỗi trình độ học vấn
    for edu in education_levels:
        edu.employee_count = Employee.objects.filter(education=edu, status='Working').count()
    
    context = {
        'education_levels': education_levels
    }
    
    return render(request, 'employee/education/education_list.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def education_create(request):
    """Tạo trình độ học vấn mới"""
    if request.method == 'POST':
        form = EducationLevelForm(request.POST)
        
        if form.is_valid():
            education = form.save()
            messages.success(request, 'Đã tạo trình độ học vấn thành công.')
            return redirect('education_list')
    else:
        form = EducationLevelForm()
    
    context = {
        'form': form,
        'title': 'Tạo trình độ học vấn'
    }
    
    return render(request, 'employee/education/education_form.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def education_update(request, pk):
    """Cập nhật trình độ học vấn hiện có"""
    education = get_object_or_404(EducationLevel, pk=pk)
    
    if request.method == 'POST':
        form = EducationLevelForm(request.POST, instance=education)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật trình độ học vấn thành công.')
            return redirect('education_list')
    else:
        form = EducationLevelForm(instance=education)
    
    context = {
        'form': form,
        'education': education,
        'title': 'Cập nhật trình độ học vấn'
    }
    
    return render(request, 'employee/education/education_form.html', context)

@login_required
@check_module_permission('organization', 'Delete')
def education_delete(request, pk):
    """Xóa trình độ học vấn"""
    education = get_object_or_404(EducationLevel, pk=pk)
    
    # Kiểm tra xem trình độ học vấn có nhân viên không
    if Employee.objects.filter(education=education).exists():
        messages.error(request, 'Không thể xóa trình độ học vấn có nhân viên.')
        return redirect('education_list')
    
    if request.method == 'POST':
        education.delete()
        messages.success(request, 'Đã xóa trình độ học vấn thành công.')
        return redirect('education_list')
    
    context = {
        'education': education
    }
    
    return render(request, 'employee/education/education_confirm_delete.html', context)

# -----------------------------------------------------------------------------
# QUẢN LÝ HỌC HÀM HỌC VỊ
# -----------------------------------------------------------------------------

@login_required
@check_module_permission('organization', 'View')
def title_list(request):
    """Danh sách tất cả học hàm học vị"""
    titles = AcademicTitle.objects.all().order_by('title_name')
    
    # Lấy số lượng nhân viên cho mỗi học hàm học vị
    for title in titles:
        title.employee_count = Employee.objects.filter(title=title, status='Working').count()
    
    context = {
        'titles': titles
    }
    
    return render(request, 'employee/title/title_list.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def title_create(request):
    """Tạo học hàm học vị mới"""
    if request.method == 'POST':
        form = AcademicTitleForm(request.POST)
        
        if form.is_valid():
            title = form.save()
            messages.success(request, 'Đã tạo học hàm học vị thành công.')
            return redirect('title_list')
    else:
        form = AcademicTitleForm()
    
    context = {
        'form': form,
        'title_text': 'Tạo học hàm học vị'
    }
    
    return render(request, 'employee/title/title_form.html', context)

@login_required
@check_module_permission('organization', 'Edit')
def title_update(request, pk):
    """Cập nhật học hàm học vị hiện có"""
    title = get_object_or_404(AcademicTitle, pk=pk)
    
    if request.method == 'POST':
        form = AcademicTitleForm(request.POST, instance=title)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật học hàm học vị thành công.')
            return redirect('title_list')
    else:
        form = AcademicTitleForm(instance=title)
    
    context = {
        'form': form,
        'academic_title': title,
        'title_text': 'Cập nhật học hàm học vị'
    }
    
    return render(request, 'employee/title/title_form.html', context)

@login_required
@check_module_permission('organization', 'Delete')
def title_delete(request, pk):
    """Xóa học hàm học vị"""
    title = get_object_or_404(AcademicTitle, pk=pk)
    
    # Kiểm tra xem học hàm học vị có nhân viên không
    if Employee.objects.filter(title=title).exists():
        messages.error(request, 'Không thể xóa học hàm học vị có nhân viên.')
        return redirect('title_list')
    
    if request.method == 'POST':
        title.delete()
        messages.success(request, 'Đã xóa học hàm học vị thành công.')
        return redirect('title_list')
    
    context = {
        'academic_title': title
    }
    
    return render(request, 'employee/title/title_confirm_delete.html', context)

# -----------------------------------------------------------------------------
# NHẬP/XUẤT DỮ LIỆU
# -----------------------------------------------------------------------------

@login_required
@hr_required
def export_employees(request):
    """Xuất nhân viên dưới dạng CSV hoặc Excel"""
    format_type = request.GET.get('format', 'csv')
    
    # Áp dụng các bộ lọc từ request nếu có
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
    
    # Xác định các trường để xuất
    fields = [
        {'field': 'employee_id', 'display': 'ID'},
        {'field': 'full_name', 'display': 'Họ tên'},
        {'field': 'email', 'display': 'Email'},
        {'field': 'phone', 'display': 'Điện thoại'},
        {'field': 'date_of_birth', 'display': 'Ngày sinh'},
        {'field': 'gender', 'display': 'Giới tính'},
        {'field': 'department.department_name', 'display': 'Phòng ban'},
        {'field': 'position.position_name', 'display': 'Vị trí'},
        {'field': 'hire_date', 'display': 'Ngày tuyển dụng'},
        {'field': 'id_card', 'display': 'CMND/CCCD'},
        {'field': 'address', 'display': 'Địa chỉ'},
        {'field': 'status', 'display': 'Trạng thái'}
    ]
    
    file_name = f"danh_sach_nhan_vien_{datetime.now().strftime('%Y%m%d')}"
    
    if format_type == 'excel':
        return ExportHelper.export_as_excel(employees, fields, file_name)
    else:
        return ExportHelper.export_as_csv(employees, fields, file_name)

@login_required
@hr_required
def import_employees(request):
    """Nhập nhân viên từ file CSV"""
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Vui lòng tải lên tệp CSV')
            return redirect('employee_list')
        
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            success_count = 0
            error_count = 0
            errors = []
            
            for row_num, row in enumerate(reader, start=2):  # Bắt đầu từ 2 để tính đến hàng tiêu đề
                try:
                    email = row.get('Email', '').strip()
                    full_name = row.get('Họ tên', '').strip()
                    
                    if not email or not full_name:
                        error_count += 1
                        errors.append(f"Dòng {row_num}: Thiếu trường bắt buộc (Email hoặc Họ tên)")
                        continue
                    
                    # Kiểm tra xem nhân viên đã tồn tại chưa
                    if Employee.objects.filter(email=email).exists():
                        employee = Employee.objects.get(email=email)
                        # Cập nhật nhân viên hiện có
                        employee.full_name = full_name
                        employee.phone = row.get('Điện thoại', '').strip()
                        
                        # Cập nhật các trường khác nếu được cung cấp
                        if row.get('Ngày sinh'):
                            try:
                                employee.date_of_birth = datetime.strptime(row.get('Ngày sinh'), '%Y-%m-%d').date()
                            except ValueError:
                                pass
                        
                        if row.get('Giới tính'):
                            gender = row.get('Giới tính').strip()
                            if gender in ['Nam', 'Nữ', 'Khác']:
                                employee.gender = gender
                        
                        if row.get('Phòng ban'):
                            dept_name = row.get('Phòng ban').strip()
                            dept = Department.objects.filter(department_name=dept_name).first()
                            if dept:
                                employee.department = dept
                        
                        if row.get('Vị trí'):
                            pos_name = row.get('Vị trí').strip()
                            pos = Position.objects.filter(position_name=pos_name).first()
                            if pos:
                                employee.position = pos
                        
                        if row.get('Ngày tuyển dụng'):
                            try:
                                employee.hire_date = datetime.strptime(row.get('Ngày tuyển dụng'), '%Y-%m-%d').date()
                            except ValueError:
                                pass
                        
                        employee.save()
                    else:
                        # Tạo nhân viên mới
                        employee = Employee(
                            full_name=full_name,
                            email=email,
                            phone=row.get('Điện thoại', '').strip()
                        )
                        
                        # Thiết lập các trường khác nếu được cung cấp
                        if row.get('Ngày sinh'):
                            try:
                                employee.date_of_birth = datetime.strptime(row.get('Ngày sinh'), '%Y-%m-%d').date()
                            except ValueError:
                                pass
                        
                        if row.get('Giới tính'):
                            gender = row.get('Giới tính').strip()
                            if gender in ['Nam', 'Nữ', 'Khác']:
                                employee.gender = gender
                        
                        if row.get('Phòng ban'):
                            dept_name = row.get('Phòng ban').strip()
                            dept = Department.objects.filter(department_name=dept_name).first()
                            if dept:
                                employee.department = dept
                        
                        if row.get('Vị trí'):
                            pos_name = row.get('Vị trí').strip()
                            pos = Position.objects.filter(position_name=pos_name).first()
                            if pos:
                                employee.position = pos
                        
                        if row.get('Ngày tuyển dụng'):
                            try:
                                employee.hire_date = datetime.strptime(row.get('Ngày tuyển dụng'), '%Y-%m-%d').date()
                            except ValueError:
                                pass
                        
                        employee.save()
                    
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append(f"Dòng {row_num}: {str(e)}")
            
            if error_count:
                messages.warning(request, f'Đã nhập {success_count} nhân viên với {error_count} lỗi.')
            else:
                messages.success(request, f'Đã nhập thành công {success_count} nhân viên.')
            
            if errors:
                request.session['import_errors'] = errors
                return redirect('import_errors')
            
            return redirect('employee_list')
            
        except Exception as e:
            messages.error(request, f'Lỗi xử lý tệp CSV: {str(e)}')
    
    # Lấy nội dung CSV mẫu
    sample_csv = "Họ tên,Email,Điện thoại,Ngày sinh,Giới tính,Phòng ban,Vị trí,Ngày tuyển dụng\n"
    sample_csv += "Nguyễn Văn A,nguyenvana@example.com,1234567890,1990-01-01,Nam,CNTT,Lập trình viên,2020-01-15\n"
    sample_csv += "Lê Thị B,lethib@example.com,9876543210,1992-05-20,Nữ,Nhân sự,Quản lý,2019-11-10"
    
    context = {
        'sample_csv': sample_csv
    }
    
    return render(request, 'employee/import_employees.html', context)

@login_required
@hr_required
def import_errors(request):
    """Hiển thị lỗi từ quá trình nhập dữ liệu"""
    errors = request.session.get('import_errors', [])
    
    if not errors:
        return redirect('employee_list')
    
    # Xóa khỏi session
    if 'import_errors' in request.session:
        del request.session['import_errors']
    
    context = {
        'errors': errors
    }
    
    return render(request, 'employee/import_errors.html', context)
