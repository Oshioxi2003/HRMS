document.addEventListener('DOMContentLoaded', function() {
    // Xử lý xác nhận hủy yêu cầu nghỉ phép
    const cancelButtons = document.querySelectorAll('a[href*="leave_request_cancel"]');
    cancelButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const requestId = this.getAttribute('href').split('/').filter(Boolean).pop();
            
            Swal.fire({
                title: 'Xác nhận hủy yêu cầu?',
                text: 'Bạn có chắc chắn muốn hủy yêu cầu nghỉ phép này không?',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#e74a3b',
                cancelButtonColor: '#858796',
                confirmButtonText: 'Có, hủy yêu cầu!',
                cancelButtonText: 'Không, giữ lại'
            }).then((result) => {
                if (result.isConfirmed) {
                    window.location.href = this.getAttribute('href');
                }
            });
        });
    });

    // Tạo tooltips cho các nút hành động
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

    // Hiệu ứng hover cho thẻ thống kê
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 .5rem 1.5rem 0 rgba(58,59,69,.2)';
            this.style.transition = 'all 0.3s ease';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 .15rem 1.75rem 0 rgba(58,59,69,.15)';
        });
    });

    // Hiển thị thông báo khi lọc được áp dụng
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter && statusFilter.value) {
        const statusText = statusFilter.options[statusFilter.selectedIndex].text;
        
        const container = document.querySelector('.leave-container');
        const notification = document.createElement('div');
        notification.className = 'alert alert-info alert-dismissible fade show notification mb-4';
        notification.innerHTML = `
            <i class="fas fa-filter me-2"></i> Đang hiển thị các yêu cầu có trạng thái: <strong>${statusText}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        container.insertBefore(notification, container.firstChild);
    }

    // Cập nhật số ngày khi thay đổi các ngày trong biểu mẫu tạo yêu cầu
    if (document.getElementById('id_start_date') && document.getElementById('id_end_date')) {
        const startDateInput = document.getElementById('id_start_date');
        const endDateInput = document.getElementById('id_end_date');
        const leaveDaysDisplay = document.getElementById('leave_days_calculation');
        
        function calculateLeaveDays() {
            if (startDateInput.value && endDateInput.value) {
                const startDate = new Date(startDateInput.value);
                const endDate = new Date(endDateInput.value);
                
                // Kiểm tra ngày hợp lệ
                if (endDate < startDate) {
                    leaveDaysDisplay.textContent = 'Ngày kết thúc phải sau ngày bắt đầu';
                    leaveDaysDisplay.classList.add('text-danger');
                    return;
                }
                
                // Tính số ngày nghỉ (đơn giản hóa - không tính cuối tuần)
                const diffTime = Math.abs(endDate - startDate);
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
                
                leaveDaysDisplay.textContent = `Số ngày nghỉ: ${diffDays} ngày`;
                leaveDaysDisplay.classList.remove('text-danger');
                leaveDaysDisplay.classList.add('text-primary');
            }
        }
        
        startDateInput.addEventListener('change', calculateLeaveDays);
        endDateInput.addEventListener('change', calculateLeaveDays);
    }

    // Hiện thị xác nhận khi yêu cầu được phê duyệt/từ chối
    // (Đối với trang quản lý nghỉ phép của quản lý)
    const approveButtons = document.querySelectorAll('.approve-leave-btn');
    const rejectButtons = document.querySelectorAll('.reject-leave-btn');
    
    approveButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            Swal.fire({
                title: 'Xác nhận phê duyệt?',
                text: 'Bạn có chắc chắn muốn phê duyệt yêu cầu nghỉ phép này?',
                icon: 'question',
                showCancelButton: true,
                confirmButtonColor: '#1cc88a',
                cancelButtonColor: '#858796',
                confirmButtonText: 'Có, phê duyệt!',
                cancelButtonText: 'Không, xem xét lại'
            }).then((result) => {
                if (result.isConfirmed) {
                    window.location.href = this.getAttribute('href');
                }
            });
        });
    });
    
    rejectButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            Swal.fire({
                title: 'Xác nhận từ chối?',
                text: 'Bạn có chắc chắn muốn từ chối yêu cầu nghỉ phép này?',
                icon: 'warning',
                input: 'text',
                inputPlaceholder: 'Nhập lý do từ chối (tuỳ chọn)',
                showCancelButton: true,
                confirmButtonColor: '#e74a3b',
                cancelButtonColor: '#858796',
                confirmButtonText: 'Có, từ chối!',
                cancelButtonText: 'Không, xem xét lại'
            }).then((result) => {
                if (result.isConfirmed) {
                    const reason = result.value || '';
                    window.location.href = this.getAttribute('href') + '?reason=' + encodeURIComponent(reason);
                }
            });
        });
    });
});

// Hàm điều chỉnh layout tương thích với màn hình điện thoại
function adjustMobileLayout() {
    const width = window.innerWidth;
    
    if (width < 768) {
        // Điều chỉnh kiểu hiển thị trên điện thoại
        document.querySelectorAll('.table thead th').forEach(th => {
            th.style.fontSize = '0.75rem';
        });
        
        document.querySelectorAll('.stat-card').forEach(card => {
            card.style.marginBottom = '1rem';
        });
    } else {
        // Khôi phục kiểu hiển thị trên máy tính
        document.querySelectorAll('.table thead th').forEach(th => {
            th.style.fontSize = '0.85rem';
        });
        
        document.querySelectorAll('.stat-card').forEach(card => {
            card.style.marginBottom = '0';
        });
    }
}

// Chạy khi tải trang và khi thay đổi kích thước cửa sổ
window.addEventListener('load', adjustMobileLayout);
window.addEventListener('resize', adjustMobileLayout);