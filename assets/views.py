from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import date, timedelta

from django.http import HttpResponse
import csv
import xlwt
import json

from .models import *
from .forms import *
from employee.models import Employee
from accounts.decorators import *
from notifications.services import create_notification

@login_required
@check_module_permission('assets', 'View')
def asset_list(request):
    """List all assets with filtering options"""
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    query = request.GET.get('q', '')
    
    assets = Asset.objects.all()
    
    if category_filter:
        assets = assets.filter(category_id=category_filter)
    
    if status_filter:
        assets = assets.filter(status=status_filter)
    
    if query:
        assets = assets.filter(
            Q(asset_tag__icontains=query) |
            Q(asset_name__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(model_number__icontains=query)
        )
    
    # Order by updated date (most recently updated first)
    assets = assets.order_by('-updated_date')
    
    # Get categories for filter dropdown
    categories = AssetCategory.objects.filter(is_active=True)
    
    # Status counts for summary
    status_counts = {
        'total': assets.count(),
        'available': assets.filter(status='Available').count(),
        'assigned': assets.filter(status='Assigned').count(),
        'maintenance': assets.filter(status='Under Maintenance').count(),
        'retired': assets.filter(status='Retired').count(),
    }
    
    return render(request, 'assets/asset_list.html', {
        'assets': assets,
        'categories': categories,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'query': query,
        'status_counts': status_counts
    })

@login_required
@hr_required
def create_asset(request):
    """Create a new asset"""
    if request.method == 'POST':
        form = AssetForm(request.POST)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.created_by = request.user
            asset.save()
            
            messages.success(request, "Asset created successfully.")
            return redirect('asset_detail', asset_id=asset.asset_id)
    else:
        # Generate unique asset tag (example: AST-{YEAR}-{SEQUENCE})
        year = date.today().year
        last_asset = Asset.objects.filter(asset_tag__startswith=f'AST-{year}-').order_by('-asset_tag').first()
        
        if last_asset:
            try:
                seq = int(last_asset.asset_tag.split('-')[-1]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        
        asset_tag = f'AST-{year}-{seq:04d}'
        form = AssetForm(initial={'asset_tag': asset_tag})
    
    return render(request, 'assets/create_asset.html', {'form': form})

@login_required
@check_module_permission('assets', 'View')
def asset_detail(request, asset_id):
    """View asset details"""
    asset = get_object_or_404(Asset, asset_id=asset_id)
    
    # Get assignment history
    assignments = AssetAssignment.objects.filter(asset=asset).order_by('-assignment_date')
    
    # Get maintenance history
    maintenance_records = AssetMaintenance.objects.filter(asset=asset).order_by('-start_date')
    
    # Determine if user can edit/assign this asset
    can_edit = request.user.role in ['HR', 'Admin']
    can_assign = request.user.role in ['HR', 'Admin'] and asset.status == 'Available'
    can_maintain = request.user.role in ['HR', 'Admin']
    
    return render(request, 'assets/asset_detail.html', {
        'asset': asset,
        'assignments': assignments,
        'maintenance_records': maintenance_records,
        'can_edit': can_edit,
        'can_assign': can_assign,
        'can_maintain': can_maintain
    })

@login_required
@hr_required
def assign_asset(request, asset_id):
    """Assign an asset to an employee"""
    asset = get_object_or_404(Asset, asset_id=asset_id)
    
    # Check if asset is available
    if asset.status != 'Available':
        messages.error(request, f"This asset is currently {asset.status} and cannot be assigned.")
        return redirect('asset_detail', asset_id=asset_id)
    
    if request.method == 'POST':
        form = AssetAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.asset = asset
            assignment.assigned_by = request.user
            assignment.status = 'Assigned'
            assignment.save()
            
            # Update asset status and current holder
            asset.status = 'Assigned'
            asset.current_holder = assignment.employee
            asset.save()
            
            # Send notification to employee
            from django.contrib.auth import get_user_model
            User = get_user_model()
            employee_user = User.objects.filter(employee=assignment.employee).first()
            
            if employee_user:
                create_notification(
                    user=employee_user,
                    notification_type='Asset',
                    title='Asset Assigned to You',
                    message=f'You have been assigned {asset.asset_name} (#{asset.asset_tag}).',
                    link=f'/assets/my-assets/'
                )
            
            messages.success(request, "Asset assigned successfully.")
            return redirect('asset_detail', asset_id=asset_id)
    else:
        form = AssetAssignmentForm(initial={'assignment_date': date.today()})
    
    return render(request, 'assets/assign_asset.html', {
        'form': form,
        'asset': asset
    })

@login_required
@hr_required
def return_asset(request, assignment_id):
    """Process the return of an assigned asset"""
    assignment = get_object_or_404(AssetAssignment, assignment_id=assignment_id, status='Assigned')
    asset = assignment.asset
    
    if request.method == 'POST':
        form = AssetReturnForm(request.POST, instance=assignment)
        if form.is_valid():
            return_process = form.save(commit=False)
            return_process.status = 'Returned'
            return_process.actual_return_date = date.today()
            return_process.save()
            
            # Update asset status and condition
            asset.status = 'Available'
            asset.condition = return_process.return_condition
            asset.current_holder = None
            asset.save()
            
            messages.success(request, "Asset return processed successfully.")
            return redirect('asset_detail', asset_id=asset.asset_id)
    else:
        form = AssetReturnForm(instance=assignment)
    
    return render(request, 'assets/return_asset.html', {
        'form': form,
        'assignment': assignment,
        'asset': asset
    })

@login_required
@employee_approved_required
def my_assets(request):
    """View assets assigned to the employee"""
    if not request.user.employee:
        messages.error(request, "You don't have an employee profile.")
        return redirect('dashboard')
    
    # Get active assignments
    active_assignments = AssetAssignment.objects.filter(
        employee=request.user.employee,
        status='Assigned'
    ).select_related('asset')
    
    # Get past assignments
    past_assignments = AssetAssignment.objects.filter(
        employee=request.user.employee,
        status='Returned'
    ).select_related('asset').order_by('-actual_return_date')
    
    # Get pending requests
    pending_requests = AssetRequest.objects.filter(
        employee=request.user.employee,
        status__in=['Pending', 'Approved']
    ).order_by('-requested_date')
    
    return render(request, 'assets/my_assets.html', {
        'active_assignments': active_assignments,
        'past_assignments': past_assignments,
        'pending_requests': pending_requests
    })

@login_required
def request_asset(request):
    """Request a new asset"""
    if not request.user.employee:
        messages.error(request, "You don't have an employee profile.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AssetRequestForm(request.POST)
        if form.is_valid():
            asset_request = form.save(commit=False)
            asset_request.employee = request.user.employee
            asset_request.status = 'Pending'
            asset_request.save()
            
            # Send notification to HR
            from django.contrib.auth import get_user_model
            User = get_user_model()
            hr_users = User.objects.filter(role='HR', is_active=True)
            
            for hr_user in hr_users:
                create_notification(
                    user=hr_user,
                    notification_type='Asset',
                    title='New Asset Request',
                    message=f'{request.user.employee.full_name} has requested a new asset: {asset_request.asset_name}',
                    link=f'/assets/requests/'
                )
            
            messages.success(request, "Asset request submitted successfully.")
            return redirect('my_assets')
    else:
        form = AssetRequestForm(initial={'needed_from': date.today() + timedelta(days=7)})
    
    return render(request, 'assets/request_asset.html', {'form': form})

@login_required
@hr_required
def asset_maintenance(request, asset_id):
    """Schedule or record maintenance for an asset"""
    asset = get_object_or_404(Asset, asset_id=asset_id)
    
    if request.method == 'POST':
        form = AssetMaintenanceForm(request.POST)
        if form.is_valid():
            maintenance = form.save(commit=False)
            maintenance.asset = asset
            maintenance.created_by = request.user
            maintenance.save()
            
            # Update asset status if maintenance is starting now
            if maintenance.status == 'In Progress':
                asset.status = 'Under Maintenance'
                asset.save()
            
            messages.success(request, "Asset maintenance scheduled/recorded successfully.")
            return redirect('asset_detail', asset_id=asset_id)
    else:
        form = AssetMaintenanceForm(initial={'start_date': date.today()})
    
    return render(request, 'assets/asset_maintenance.html', {
        'form': form,
        'asset': asset
    })

@login_required
@hr_required
def asset_requests(request):
    """View and process asset requests"""
    status_filter = request.GET.get('status', '')
    
    requests = AssetRequest.objects.all()
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    # Order by requested date (oldest first)
    requests = requests.order_by('requested_date')
    
    return render(request, 'assets/asset_requests.html', {
        'requests': requests,
        'status_filter': status_filter
    })

@login_required
@hr_required
def process_asset_request(request, request_id):
    """Approve or reject an asset request"""
    asset_request = get_object_or_404(AssetRequest, request_id=request_id, status='Pending')
    
    if request.method == 'POST':
        form = AssetRequestApprovalForm(request.POST, instance=asset_request)
        if form.is_valid():
            approval = form.save(commit=False)
            approval.approved_by = request.user
            approval.approval_date = date.today()
            
            # If approving and assigning an asset
            if approval.status == 'Approved' and approval.fulfilled_with:
                # Check if asset is available
                if approval.fulfilled_with.status != 'Available':
                    messages.error(request, "The selected asset is not available for assignment.")
                    return redirect('process_asset_request', request_id=request_id)
                
                # Create asset assignment
                assignment = AssetAssignment.objects.create(
                    asset=approval.fulfilled_with,
                    employee=asset_request.employee,
                    assignment_date=date.today(),
                    expected_return_date=asset_request.needed_until,
                    assigned_by=request.user,
                    assignment_notes=f"Assigned in response to asset request #{request_id}",
                    status='Assigned'
                )
                
                # Update asset status
                approval.fulfilled_with.status = 'Assigned'
                approval.fulfilled_with.current_holder = asset_request.employee
                approval.fulfilled_with.save()
                
                # Update request status
                approval.status = 'Fulfilled'
            
            approval.save()
            
            # Send notification to employee
            from django.contrib.auth import get_user_model
            User = get_user_model()
            employee_user = User.objects.filter(employee=asset_request.employee).first()
            
            if employee_user:
                if approval.status == 'Approved' or approval.status == 'Fulfilled':
                    message = f'Your request for {asset_request.asset_name} has been approved.'
                    if approval.status == 'Fulfilled':
                        message += f' Asset {approval.fulfilled_with.asset_name} has been assigned to you.'
                else:
                    message = f'Your request for {asset_request.asset_name} has been rejected: {approval.rejection_reason}'
                
                create_notification(
                    user=employee_user,
                    notification_type='Asset',
                    title=f'Asset Request {approval.status}',
                    message=message,
                    link=f'/assets/my-assets/'
                )
            
            messages.success(request, f"Asset request {approval.status.lower()} successfully.")
            return redirect('asset_requests')
    else:
        form = AssetRequestApprovalForm(instance=asset_request)
        
        # Get available assets of the requested category
        available_assets = Asset.objects.filter(status='Available')
        if asset_request.category:
            available_assets = available_assets.filter(category=asset_request.category)
    
    return render(request, 'assets/process_asset_request.html', {
        'form': form,
        'asset_request': asset_request,
        'available_assets': available_assets
    })


# Asset Management Views
@login_required
def edit_asset(request, asset_id):
    asset = get_object_or_404(Asset, asset_id=asset_id)
    
    if request.method == 'POST':
        form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            form.save()
            messages.success(request, f'Tài sản {asset.asset_name} đã được cập nhật thành công.')
            return redirect('asset_detail', asset_id=asset.asset_id)
    else:
        form = AssetForm(instance=asset)
    
    return render(request, 'assets/asset_form.html', {
        'form': form,
        'asset': asset,
        'title': 'Chỉnh sửa tài sản'
    })

@login_required
def delete_asset(request, asset_id):
    asset = get_object_or_404(Asset, asset_id=asset_id)
    
    if request.method == 'POST':
        asset_name = asset.asset_name
        asset.delete()
        messages.success(request, f'Tài sản {asset_name} đã được xóa thành công.')
        return redirect('asset_list')
    
    return render(request, 'assets/asset_confirm_delete.html', {
        'asset': asset
    })

# Asset Maintenance Views
@login_required
def edit_maintenance(request, maintenance_id):
    maintenance = get_object_or_404(AssetMaintenance, maintenance_id=maintenance_id)
    asset = maintenance.asset
    
    if request.method == 'POST':
        form = AssetMaintenanceForm(request.POST, instance=maintenance)
        if form.is_valid():
            maintenance = form.save(commit=False)
            maintenance.save()
            messages.success(request, f'Thông tin bảo trì đã được cập nhật thành công.')
            return redirect('asset_detail', asset_id=asset.asset_id)
    else:
        form = AssetMaintenanceForm(instance=maintenance)
    
    return render(request, 'assets/maintenance_form.html', {
        'form': form,
        'asset': asset,
        'maintenance': maintenance,
        'title': 'Chỉnh sửa thông tin bảo trì'
    })

@login_required
def complete_maintenance(request, maintenance_id):
    maintenance = get_object_or_404(AssetMaintenance, maintenance_id=maintenance_id)
    asset = maintenance.asset
    
    if request.method == 'POST':
        maintenance.status = 'Completed'
        maintenance.end_date = timezone.now().date()
        maintenance.save()
        
        # Cập nhật trạng thái tài sản từ "Under Maintenance" thành "Available"
        if asset.status == 'Under Maintenance':
            asset.status = 'Available'
            asset.save()
        
        messages.success(request, f'Bảo trì đã được hoàn thành thành công.')
        return redirect('asset_detail', asset_id=asset.asset_id)
    
    return render(request, 'assets/maintenance_complete.html', {
        'maintenance': maintenance,
        'asset': asset
    })

# Asset Category Views
@login_required
def asset_category_list(request):
    categories = AssetCategory.objects.all()
    
    # Thêm số lượng tài sản cho mỗi danh mục
    for category in categories:
        category.asset_count = Asset.objects.filter(category=category).count()
    
    return render(request, 'assets/category_list.html', {
        'categories': categories,
        'title': 'Danh mục tài sản'
    })

@login_required
def asset_category_create(request):
    if request.method == 'POST':
        form = AssetCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.save()
            messages.success(request, f'Danh mục {category.name} đã được tạo thành công.')
            return redirect('asset_category_list')
    else:
        form = AssetCategoryForm()
    
    return render(request, 'assets/category_form.html', {
        'form': form,
        'title': 'Tạo danh mục mới'
    })

@login_required
def asset_category_edit(request, category_id):
    category = get_object_or_404(AssetCategory, category_id=category_id)
    
    if request.method == 'POST':
        form = AssetCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Danh mục {category.name} đã được cập nhật thành công.')
            return redirect('asset_category_list')
    else:
        form = AssetCategoryForm(instance=category)
    
    return render(request, 'assets/category_form.html', {
        'form': form,
        'category': category,
        'title': 'Chỉnh sửa danh mục'
    })

@login_required
def asset_category_delete(request, category_id):
    category = get_object_or_404(AssetCategory, category_id=category_id)
    
    # Kiểm tra xem danh mục có tài sản nào không
    asset_count = Asset.objects.filter(category=category).count()
    
    if request.method == 'POST':
        if asset_count > 0:
            messages.error(request, f'Không thể xóa danh mục {category.name} vì có {asset_count} tài sản thuộc danh mục này.')
            return redirect('asset_category_list')
        
        category_name = category.name
        category.delete()
        messages.success(request, f'Danh mục {category_name} đã được xóa thành công.')
        return redirect('asset_category_list')
    
    return render(request, 'assets/category_confirm_delete.html', {
        'category': category,
        'asset_count': asset_count
    })

# Report Views
@login_required
def asset_report(request):
    # Tổng số tài sản theo danh mục
    categories = AssetCategory.objects.annotate(asset_count=Count('asset'))
    
    # Tổng số tài sản theo trạng thái
    status_counts = Asset.objects.values('status').annotate(count=Count('status'))
    
    # Tổng số tài sản theo tình trạng
    condition_counts = Asset.objects.values('condition').annotate(count=Count('condition'))
    
    # Tổng giá trị tài sản
    total_value = Asset.objects.aggregate(total=Sum('purchase_cost'))['total'] or 0
    
    # Top 5 tài sản có giá trị cao nhất
    top_assets = Asset.objects.filter(purchase_cost__isnull=False).order_by('-purchase_cost')[:5]
    
    # Tài sản sắp hết hạn bảo hành (trong 30 ngày tới)
    today = timezone.now().date()
    expiring_warranty = Asset.objects.filter(
        warranty_expiry__isnull=False,
        warranty_expiry__gt=today,
        warranty_expiry__lte=today + timezone.timedelta(days=30)
    )
    
    return render(request, 'assets/asset_report.html', {
        'categories': categories,
        'status_counts': status_counts,
        'condition_counts': condition_counts,
        'total_value': total_value,
        'top_assets': top_assets,
        'expiring_warranty': expiring_warranty,
        'title': 'Báo cáo tài sản'
    })

@login_required
def export_assets(request):
    format_type = request.GET.get('format', 'csv')
    
    # Lấy tất cả tài sản
    assets = Asset.objects.all().select_related('category', 'current_holder', 'created_by')
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="assets.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Mã tài sản', 'Tên tài sản', 'Danh mục', 'Số sê-ri', 
            'Ngày mua', 'Giá mua', 'Hạn bảo hành', 'Vị trí', 'Trạng thái', 
            'Tình trạng', 'Người giữ hiện tại'
        ])
        
        for asset in assets:
            writer.writerow([
                asset.asset_id, 
                asset.asset_tag, 
                asset.asset_name, 
                asset.category.name if asset.category else '', 
                asset.serial_number or '', 
                asset.purchase_date or '', 
                asset.purchase_cost or '', 
                asset.warranty_expiry or '', 
                asset.location or '', 
                asset.status, 
                asset.condition, 
                asset.current_holder.full_name if asset.current_holder else ''
            ])
        
        return response
    
    elif format_type == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="assets.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Assets')
        
        # Định dạng tiêu đề
        font_style = xlwt.XFStyle()
        font_style.font.bold = True
        
        columns = [
            'ID', 'Mã tài sản', 'Tên tài sản', 'Danh mục', 'Số sê-ri', 
            'Ngày mua', 'Giá mua', 'Hạn bảo hành', 'Vị trí', 'Trạng thái', 
            'Tình trạng', 'Người giữ hiện tại'
        ]
        
        for col_num, column_title in enumerate(columns):
            ws.write(0, col_num, column_title, font_style)
        
        # Định dạng nội dung
        font_style = xlwt.XFStyle()
        
        row_num = 1
        for asset in assets:
            ws.write(row_num, 0, asset.asset_id, font_style)
            ws.write(row_num, 1, asset.asset_tag, font_style)
            ws.write(row_num, 2, asset.asset_name, font_style)
            ws.write(row_num, 3, asset.category.name if asset.category else '', font_style)
            ws.write(row_num, 4, asset.serial_number or '', font_style)
            ws.write(row_num, 5, str(asset.purchase_date) if asset.purchase_date else '', font_style)
            ws.write(row_num, 6, float(asset.purchase_cost) if asset.purchase_cost else 0, font_style)
            ws.write(row_num, 7, str(asset.warranty_expiry) if asset.warranty_expiry else '', font_style)
            ws.write(row_num, 8, asset.location or '', font_style)
            ws.write(row_num, 9, asset.status, font_style)
            ws.write(row_num, 10, asset.condition, font_style)
            ws.write(row_num, 11, asset.current_holder.full_name if asset.current_holder else '', font_style)
            row_num += 1
        
        wb.save(response)
        return response
    
    elif format_type == 'json':
        assets_data = []
        
        for asset in assets:
            assets_data.append({
                'id': asset.asset_id,
                'asset_tag': asset.asset_tag,
                'asset_name': asset.asset_name,
                'category': asset.category.name if asset.category else None,
                'serial_number': asset.serial_number,
                'purchase_date': str(asset.purchase_date) if asset.purchase_date else None,
                'purchase_cost': str(asset.purchase_cost) if asset.purchase_cost else None,
                'warranty_expiry': str(asset.warranty_expiry) if asset.warranty_expiry else None,
                'location': asset.location,
                'status': asset.status,
                'condition': asset.condition,
                'current_holder': asset.current_holder.full_name if asset.current_holder else None
            })
        
        response = HttpResponse(json.dumps(assets_data, indent=4), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="assets.json"'
        return response
    
    # Mặc định trả về CSV nếu định dạng không được hỗ trợ
    return redirect('asset_list')