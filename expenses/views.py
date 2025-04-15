from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count
from django.forms import modelformset_factory
from django.core.paginator import Paginator
import csv
import xlwt
import json
from datetime import datetime, date

from .models import ExpenseCategory, ExpenseClaim, ExpenseItem
from .forms import (
    ExpenseCategoryForm, ExpenseClaimForm, ExpenseItemForm,
    ExpenseApprovalForm, ExpensePaymentForm
)
from employee.models import Employee
from accounts.decorators import employee_approved_required

# Hàm kiểm tra quyền quản lý
def is_manager_or_hr(user):
    if not hasattr(user, 'employee'):
        return False
    return user.employee.is_manager or user.employee.department.name.lower() == 'hr'

# Employee expense management views
@login_required
@employee_approved_required
def my_expenses(request):
    """Hiển thị danh sách chi phí của nhân viên đăng nhập"""
    employee = request.user.employee
    expenses = ExpenseClaim.objects.filter(employee=employee).order_by('-created_date')
    
    # Thống kê nhanh
    total_claimed = expenses.filter(status__in=['Submitted', 'Approved', 'Paid']).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_approved = expenses.filter(status__in=['Approved', 'Paid']).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_paid = expenses.filter(status='Paid').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Phân trang
    paginator = Paginator(expenses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'expenses/my_expenses.html', {
        'expenses': page_obj,
        'total_claimed': total_claimed,
        'total_approved': total_approved,
        'total_paid': total_paid,
        'title': 'Chi phí của tôi'
    })

@login_required
@employee_approved_required
def create_expense_claim(request):
    """Tạo yêu cầu chi phí mới"""
    if request.method == 'POST':
        form = ExpenseClaimForm(request.POST)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.employee = request.user.employee
            claim.save()
            messages.success(request, 'Yêu cầu chi phí đã được tạo. Hãy thêm các khoản chi phí.')
            return redirect('add_expense_items', claim_id=claim.claim_id)
    else:
        form = ExpenseClaimForm()
    
    return render(request, 'expenses/create_expense_claim.html', {
        'form': form,
        'title': 'Tạo yêu cầu chi phí'
    })

@login_required
@employee_approved_required
def add_expense_items(request, claim_id):
    """Thêm các khoản chi phí vào yêu cầu"""
    claim = get_object_or_404(ExpenseClaim, claim_id=claim_id, employee=request.user.employee)
    
    # Không cho phép thêm khoản chi phí nếu yêu cầu không ở trạng thái Draft
    if claim.status != 'Draft':
        messages.error(request, 'Không thể thêm khoản chi phí vào yêu cầu đã gửi.')
        return redirect('view_expense_claim', claim_id=claim.claim_id)
    
    if request.method == 'POST':
        form = ExpenseItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.expense_claim = claim
            item.save()
            messages.success(request, 'Khoản chi phí đã được thêm.')
            
            # Kiểm tra nếu người dùng muốn thêm một khoản chi phí khác
            if 'add_another' in request.POST:
                return redirect('add_expense_items', claim_id=claim.claim_id)
            else:
                return redirect('view_expense_claim', claim_id=claim.claim_id)
    else:
        form = ExpenseItemForm(initial={'date': date.today()})
    
    # Lấy danh sách các khoản chi phí hiện tại
    items = ExpenseItem.objects.filter(expense_claim=claim)
    
    return render(request, 'expenses/add_expense_items.html', {
        'form': form,
        'claim': claim,
        'items': items,
        'title': 'Thêm khoản chi phí'
    })

@login_required
@employee_approved_required
def view_expense_claim(request, claim_id):
    """Xem chi tiết yêu cầu chi phí"""
    # Kiểm tra quyền truy cập
    claim = get_object_or_404(ExpenseClaim, claim_id=claim_id)
    
    # Chỉ cho phép nhân viên xem yêu cầu của họ hoặc quản lý/HR xem tất cả
    if claim.employee != request.user.employee and not is_manager_or_hr(request.user):
        messages.error(request, 'Bạn không có quyền xem yêu cầu này.')
        return redirect('my_expenses')
    
    # Lấy danh sách các khoản chi phí
    items = ExpenseItem.objects.filter(expense_claim=claim)
    
    # Nếu yêu cầu ở trạng thái Draft và là của người dùng hiện tại, hiển thị nút Submit
    can_submit = claim.status == 'Draft' and claim.employee == request.user.employee
    can_edit = claim.status == 'Draft' and claim.employee == request.user.employee
    can_cancel = claim.status in ['Draft', 'Submitted'] and claim.employee == request.user.employee
    can_approve = claim.status == 'Submitted' and is_manager_or_hr(request.user)
    can_process_payment = claim.status == 'Approved' and is_manager_or_hr(request.user)
    
    return render(request, 'expenses/view_expense_claim.html', {
        'claim': claim,
        'items': items,
        'can_submit': can_submit,
        'can_edit': can_edit,
        'can_cancel': can_cancel,
        'can_approve': can_approve,
        'can_process_payment': can_process_payment,
        'title': f'Chi tiết yêu cầu: {claim.claim_title}'
    })

@login_required
@employee_approved_required
def edit_expense_claim(request, claim_id):
    """Chỉnh sửa thông tin yêu cầu chi phí"""
    claim = get_object_or_404(ExpenseClaim, claim_id=claim_id, employee=request.user.employee)
    
    # Chỉ cho phép chỉnh sửa nếu yêu cầu ở trạng thái Draft
    if claim.status != 'Draft':
        messages.error(request, 'Không thể chỉnh sửa yêu cầu đã gửi.')
        return redirect('view_expense_claim', claim_id=claim.claim_id)
    
    if request.method == 'POST':
        form = ExpenseClaimForm(request.POST, instance=claim)
        if form.is_valid():
            form.save()
            
            # Kiểm tra nếu người dùng đã nhấn nút Submit
            if 'submit_claim' in request.POST:
                # Kiểm tra xem có khoản chi phí nào không
                if ExpenseItem.objects.filter(expense_claim=claim).exists():
                    claim.status = 'Submitted'
                    claim.submission_date = timezone.now().date()
                    claim.save()
                    messages.success(request, 'Yêu cầu chi phí đã được gửi để phê duyệt.')
                else:
                    messages.error(request, 'Không thể gửi yêu cầu chi phí không có khoản chi phí nào.')
            else:
                messages.success(request, 'Yêu cầu chi phí đã được cập nhật.')
            
            return redirect('view_expense_claim', claim_id=claim.claim_id)
    else:
        form = ExpenseClaimForm(instance=claim)
    
    return render(request, 'expenses/expense_claim_form.html', {
        'form': form,
        'claim': claim,
        'title': 'Chỉnh sửa yêu cầu chi phí'
    })

@login_required
@employee_approved_required
def delete_expense_claim(request, claim_id):
    """Xóa yêu cầu chi phí"""
    claim = get_object_or_404(ExpenseClaim, claim_id=claim_id, employee=request.user.employee)
    
    # Chỉ cho phép xóa nếu yêu cầu ở trạng thái Draft
    if claim.status != 'Draft':
        messages.error(request, 'Không thể xóa yêu cầu đã gửi.')
        return redirect('view_expense_claim', claim_id=claim.claim_id)
    
    if request.method == 'POST':
        claim.delete()
        messages.success(request, 'Yêu cầu chi phí đã được xóa.')
        return redirect('my_expenses')
    
    return render(request, 'expenses/expense_claim_confirm_delete.html', {
        'claim': claim,
        'title': 'Xóa yêu cầu chi phí'
    })

@login_required
@employee_approved_required
def cancel_expense_claim(request, claim_id):
    """Hủy yêu cầu chi phí"""
    claim = get_object_or_404(ExpenseClaim, claim_id=claim_id, employee=request.user.employee)
    
    # Chỉ cho phép hủy nếu yêu cầu ở trạng thái Draft hoặc Submitted
    if claim.status not in ['Draft', 'Submitted']:
        messages.error(request, 'Không thể hủy yêu cầu đã được phê duyệt hoặc thanh toán.')
        return redirect('view_expense_claim', claim_id=claim.claim_id)
    
    if request.method == 'POST':
        claim.status = 'Cancelled'
        claim.save()
        messages.success(request, 'Yêu cầu chi phí đã được hủy.')
        return redirect('my_expenses')
    
    return render(request, 'expenses/expense_claim_confirm_cancel.html', {
        'claim': claim,
        'title': 'Hủy yêu cầu chi phí'
    })

# Item management views
@login_required
@employee_approved_required
def edit_expense_item(request, item_id):
    """Chỉnh sửa khoản chi phí"""
    item = get_object_or_404(ExpenseItem, item_id=item_id)
    claim = item.expense_claim
    
    # Kiểm tra quyền truy cập
    if claim.employee != request.user.employee:
        messages.error(request, 'Bạn không có quyền chỉnh sửa khoản chi phí này.')
        return redirect('my_expenses')
    
    # Chỉ cho phép chỉnh sửa nếu yêu cầu ở trạng thái Draft
    if claim.status != 'Draft':
        messages.error(request, 'Không thể chỉnh sửa khoản chi phí của yêu cầu đã gửi.')
        return redirect('view_expense_claim', claim_id=claim.claim_id)
    
    if request.method == 'POST':
        form = ExpenseItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Khoản chi phí đã được cập nhật.')
            return redirect('view_expense_claim', claim_id=claim.claim_id)
    else:
        form = ExpenseItemForm(instance=item)
    
    return render(request, 'expenses/expense_item_form.html', {
        'form': form,
        'item': item,
        'claim': claim,
        'title': 'Chỉnh sửa khoản chi phí'
    })

@login_required
@employee_approved_required
def delete_expense_item(request, item_id):
    """Xóa khoản chi phí"""
    item = get_object_or_404(ExpenseItem, item_id=item_id)
    claim = item.expense_claim
    
    # Kiểm tra quyền truy cập
    if claim.employee != request.user.employee:
        messages.error(request, 'Bạn không có quyền xóa khoản chi phí này.')
        return redirect('my_expenses')
    
    # Chỉ cho phép xóa nếu yêu cầu ở trạng thái Draft
    if claim.status != 'Draft':
        messages.error(request, 'Không thể xóa khoản chi phí của yêu cầu đã gửi.')
        return redirect('view_expense_claim', claim_id=claim.claim_id)
    
    if request.method == 'POST':
        item.delete()
        # Cập nhật tổng số tiền của yêu cầu
        claim.calculate_total()
        messages.success(request, 'Khoản chi phí đã được xóa.')
        return redirect('view_expense_claim', claim_id=claim.claim_id)
    
    return render(request, 'expenses/expense_item_confirm_delete.html', {
        'item': item,
        'claim': claim,
        'title': 'Xóa khoản chi phí'
    })

# Manager/HR expense approval views
@login_required
@user_passes_test(is_manager_or_hr)
def pending_expenses(request):
    """Hiển thị danh sách yêu cầu chi phí đang chờ phê duyệt"""
    # Lấy danh sách yêu cầu chi phí đang chờ phê duyệt
    expenses = ExpenseClaim.objects.filter(status='Submitted').order_by('-submission_date')
    
    # Nếu là quản lý, chỉ hiển thị yêu cầu từ nhân viên trong phòng ban
    if request.user.employee.is_manager and not request.user.employee.department.name.lower() == 'hr':
        department = request.user.employee.department
        expenses = expenses.filter(employee__department=department)
    
    # Phân trang
    paginator = Paginator(expenses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'expenses/pending_expenses.html', {
        'expenses': page_obj,
        'title': 'Yêu cầu chi phí chờ phê duyệt'
    })

@login_required
@user_passes_test(is_manager_or_hr)
def approve_expense(request, claim_id):
    """Phê duyệt hoặc từ chối yêu cầu chi phí"""
    claim = get_object_or_404(ExpenseClaim, claim_id=claim_id, status='Submitted')
    
    # Nếu là quản lý, chỉ cho phép phê duyệt yêu cầu từ nhân viên trong phòng ban
    if request.user.employee.is_manager and not request.user.employee.department.name.lower() == 'hr':
        if claim.employee.department != request.user.employee.department:
            messages.error(request, 'Bạn không có quyền phê duyệt yêu cầu này.')
            return redirect('pending_expenses')
    
    if request.method == 'POST':
        form = ExpenseApprovalForm(request.POST, instance=claim)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.approved_by = request.user.employee
            claim.approval_date = timezone.now().date()
            claim.save()
            
            status_message = 'phê duyệt' if claim.status == 'Approved' else 'từ chối'
            messages.success(request, f'Yêu cầu chi phí đã được {status_message}.')
            return redirect('pending_expenses')
    else:
        form = ExpenseApprovalForm(instance=claim)
    
    # Lấy danh sách các khoản chi phí
    items = ExpenseItem.objects.filter(expense_claim=claim)
    
    return render(request, 'expenses/approve_expense.html', {
        'form': form,
        'claim': claim,
        'items': items,
        'title': 'Phê duyệt yêu cầu chi phí'
    })

# Payment processing views
@login_required
@user_passes_test(is_manager_or_hr)
def process_payment(request, claim_id):
    """Xử lý thanh toán cho yêu cầu chi phí đã được phê duyệt"""
    claim = get_object_or_404(ExpenseClaim, claim_id=claim_id, status='Approved')
    
    if request.method == 'POST':
        form = ExpensePaymentForm(request.POST, instance=claim)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.status = 'Paid'
            claim.save()
            messages.success(request, 'Thanh toán đã được xử lý thành công.')
            return redirect('processed_expenses')
    else:
        form = ExpensePaymentForm(instance=claim, initial={'payment_date': date.today()})
    
    return render(request, 'expenses/process_payment.html', {
        'form': form,
        'claim': claim,
        'title': 'Xử lý thanh toán'
    })

@login_required
@user_passes_test(is_manager_or_hr)
def processed_expenses(request):
    """Hiển thị danh sách yêu cầu chi phí đã được xử lý"""
    # Lấy danh sách yêu cầu chi phí đã được xử lý
    expenses = ExpenseClaim.objects.filter(status__in=['Approved', 'Rejected', 'Paid']).order_by('-updated_date')
    
    # Nếu là quản lý, chỉ hiển thị yêu cầu từ nhân viên trong phòng ban
    if request.user.employee.is_manager and not request.user.employee.department.name.lower() == 'hr':
        department = request.user.employee.department
        expenses = expenses.filter(employee__department=department)
    
    # Lọc theo trạng thái nếu có
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'All':
        expenses = expenses.filter(status=status_filter)
    
    # Phân trang
    paginator = Paginator(expenses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'expenses/processed_expenses.html', {
        'expenses': page_obj,
        'status_filter': status_filter or 'All',
        'title': 'Yêu cầu chi phí đã xử lý'
    })

# Category management views
@login_required
@user_passes_test(is_manager_or_hr)
def expense_category_list(request):
    """Hiển thị danh sách danh mục chi phí"""
    categories = ExpenseCategory.objects.all().order_by('name')
    
    # Thêm số lượng khoản chi phí cho mỗi danh mục
    for category in categories:
        category.item_count = ExpenseItem.objects.filter(category=category).count()
    
    return render(request, 'expenses/category_list.html', {
        'categories': categories,
        'title': 'Danh mục chi phí'
    })

@login_required
@user_passes_test(is_manager_or_hr)
def expense_category_create(request):
    """Tạo danh mục chi phí mới"""
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Danh mục {category.name} đã được tạo thành công.')
            return redirect('expense_category_list')
    else:
        form = ExpenseCategoryForm()
    
    return render(request, 'expenses/category_form.html', {
        'form': form,
        'title': 'Tạo danh mục chi phí mới'
    })

@login_required
@user_passes_test(is_manager_or_hr)
def expense_category_edit(request, category_id):
    """Chỉnh sửa danh mục chi phí"""
    category = get_object_or_404(ExpenseCategory, category_id=category_id)
    
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Danh mục {category.name} đã được cập nhật thành công.')
            return redirect('expense_category_list')
    else:
        form = ExpenseCategoryForm(instance=category)
    
    return render(request, 'expenses/category_form.html', {
        'form': form,
        'category': category,
        'title': 'Chỉnh sửa danh mục chi phí'
    })

@login_required
@user_passes_test(is_manager_or_hr)
def expense_category_delete(request, category_id):
    """Xóa danh mục chi phí"""
    category = get_object_or_404(ExpenseCategory, category_id=category_id)
    
    # Kiểm tra xem danh mục có khoản chi phí nào không
    item_count = ExpenseItem.objects.filter(category=category).count()
    
    if request.method == 'POST':
        if item_count > 0:
            messages.error(request, f'Không thể xóa danh mục {category.name} vì có {item_count} khoản chi phí thuộc danh mục này.')
            return redirect('expense_category_list')
        
        category_name = category.name
        category.delete()
        messages.success(request, f'Danh mục {category_name} đã được xóa thành công.')
        return redirect('expense_category_list')
    
    return render(request, 'expenses/category_confirm_delete.html', {
        'category': category,
        'item_count': item_count,
        'title': 'Xóa danh mục chi phí'
    })

# Report views
@login_required
@user_passes_test(is_manager_or_hr)
def expense_report(request):
    """Hiển thị báo cáo chi phí"""
    # Lấy tham số từ request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    department_id = request.GET.get('department')
    
    # Nếu không có ngày bắt đầu và kết thúc, sử dụng tháng hiện tại
    if not start_date or not end_date:
        today = timezone.now().date()
        start_date = date(today.year, today.month, 1).strftime('%Y-%m-%d')
        # Ngày cuối cùng của tháng
        if today.month == 12:
            end_date = date(today.year + 1, 1, 1)
        else:
            end_date = date(today.year, today.month + 1, 1)
        end_date = (end_date - timezone.timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Lọc yêu cầu chi phí theo ngày
    expenses = ExpenseClaim.objects.filter(
        submission_date__gte=start_date,
        submission_date__lte=end_date,
        status__in=['Approved', 'Paid']
    )
    
    # Nếu là quản lý, chỉ hiển thị yêu cầu từ nhân viên trong phòng ban
    if request.user.employee.is_manager and not request.user.employee.department.name.lower() == 'hr':
        department = request.user.employee.department
        expenses = expenses.filter(employee__department=department)
    # Nếu có lọc theo phòng ban
    elif department_id:
        expenses = expenses.filter(employee__department_id=department_id)
    
    # Tính tổng chi phí
    total_amount = expenses.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Tính chi phí theo danh mục
    expense_items = ExpenseItem.objects.filter(expense_claim__in=expenses)
    category_expenses = expense_items.values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    # Tính chi phí theo nhân viên
    employee_expenses = expenses.values('employee__full_name').annotate(
        total=Sum('total_amount')
    ).order_by('-total')
    
    # Tính chi phí theo phòng ban
    department_expenses = expenses.values('employee__department__name').annotate(
        total=Sum('total_amount')
    ).order_by('-total')
    
    # Lấy danh sách phòng ban cho bộ lọc
    from employee.models import Department
    departments = Department.objects.all()
    
    return render(request, 'expenses/expense_report.html', {
        'expenses': expenses,
        'total_amount': total_amount,
        'category_expenses': category_expenses,
        'employee_expenses': employee_expenses,
        'department_expenses': department_expenses,
        'start_date': start_date,
        'end_date': end_date,
        'department_id': department_id,
        'departments': departments,
        'title': 'Báo cáo chi phí'
    })

@login_required
@user_passes_test(is_manager_or_hr)
def export_expenses(request):
    """Xuất dữ liệu chi phí"""
    # Lấy tham số từ request
    format_type = request.GET.get('format', 'csv')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    department_id = request.GET.get('department')
    
    # Lọc yêu cầu chi phí theo ngày
    expenses = ExpenseClaim.objects.filter(status__in=['Approved', 'Paid'])
    
    if start_date and end_date:
        expenses = expenses.filter(
            submission_date__gte=start_date,
            submission_date__lte=end_date
        )
    
    # Nếu là quản lý, chỉ xuất yêu cầu từ nhân viên trong phòng ban
    if request.user.employee.is_manager and not request.user.employee.department.name.lower() == 'hr':
        department = request.user.employee.department
        expenses = expenses.filter(employee__department=department)
    # Nếu có lọc theo phòng ban
    elif department_id:
        expenses = expenses.filter(employee__department_id=department_id)
    
    # Lấy thông tin chi tiết
    expenses = expenses.select_related('employee', 'approved_by')
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="expenses.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Nhân viên', 'Tiêu đề', 'Tổng tiền', 'Ngày gửi', 
            'Trạng thái', 'Người phê duyệt', 'Ngày phê duyệt', 'Ngày thanh toán'
        ])
        
        for expense in expenses:
            writer.writerow([
                expense.claim_id,
                expense.employee.full_name,
                expense.claim_title,
                expense.total_amount,
                expense.submission_date,
                expense.status,
                expense.approved_by.full_name if expense.approved_by else '',
                expense.approval_date or '',
                expense.payment_date or ''
            ])
        
        return response
    
    elif format_type == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="expenses.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Expenses')
        
        # Định dạng tiêu đề
        font_style = xlwt.XFStyle()
        font_style.font.bold = True
        
        columns = [
            'ID', 'Nhân viên', 'Tiêu đề', 'Tổng tiền', 'Ngày gửi', 
            'Trạng thái', 'Người phê duyệt', 'Ngày phê duyệt', 'Ngày thanh toán'
        ]
        
        for col_num, column_title in enumerate(columns):
            ws.write(0, col_num, column_title, font_style)
        
        # Định dạng nội dung
        font_style = xlwt.XFStyle()
        
        row_num = 1
        for expense in expenses:
            ws.write(row_num, 0, expense.claim_id, font_style)
            ws.write(row_num, 1, expense.employee.full_name, font_style)
            ws.write(row_num, 2, expense.claim_title, font_style)
            ws.write(row_num, 3, float(expense.total_amount), font_style)
            ws.write(row_num, 4, str(expense.submission_date), font_style)
            ws.write(row_num, 5, expense.status, font_style)
            ws.write(row_num, 6, expense.approved_by.full_name if expense.approved_by else '', font_style)
            ws.write(row_num, 7, str(expense.approval_date) if expense.approval_date else '', font_style)
            ws.write(row_num, 8, str(expense.payment_date) if expense.payment_date else '', font_style)
            row_num += 1
        
        wb.save(response)
        return response
    
    elif format_type == 'json':
        expenses_data = []
        
        for expense in expenses:
            expenses_data.append({
                'id': expense.claim_id,
                'employee': expense.employee.full_name,
                'title': expense.claim_title,
                'amount': str(expense.total_amount),
                'submission_date': str(expense.submission_date),
                'status': expense.status,
                'approved_by': expense.approved_by.full_name if expense.approved_by else None,
                'approval_date': str(expense.approval_date) if expense.approval_date else None,
                'payment_date': str(expense.payment_date) if expense.payment_date else None
            })
        
        response = HttpResponse(json.dumps(expenses_data, indent=4), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="expenses.json"'
        return response
    
    # Mặc định trả về CSV nếu định dạng không được hỗ trợ
    return redirect('expense_report')

