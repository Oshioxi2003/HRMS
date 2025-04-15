/**
 * Quản lý địa chỉ Việt Nam cho form nhân viên
 * Sử dụng API provinces.open-api.vn
 */
document.addEventListener('DOMContentLoaded', function() {
    // ===== CONSTANTS =====
    const API_PROVINCES = 'https://provinces.open-api.vn/api/p/';
    const API_DISTRICTS = 'https://provinces.open-api.vn/api/p/{province_code}?depth=2';
    const API_WARDS = 'https://provinces.open-api.vn/api/d/{district_code}?depth=2';

    // ===== ELEMENTS =====
    // Selects cho nơi cấp CMND/CCCD
    const idCardIssuePlace = document.getElementById('id_card_issue_place');
    
    // Selects cho địa chỉ quê quán
    const hometownProvince = document.getElementById('hometown_province');
    const hometownDistrict = document.getElementById('hometown_district');
    const hometownWard = document.getElementById('hometown_ward');
    const hometownAddress = document.getElementById('hometown_address');
    
    // Selects cho địa chỉ hiện tại
    const currentProvince = document.getElementById('current_province');
    const currentDistrict = document.getElementById('current_district');
    const currentWard = document.getElementById('current_ward');
    const currentAddress = document.getElementById('current_address');
    
    // Container cho nút sao chép địa chỉ
    const addressCopyContainer = document.querySelector('.address-copy-container');
    
    // ===== CACHE DATA =====
    let provincesData = [];
    let districtsCache = {};
    let wardsCache = {};
    
    // ===== FETCH FUNCTIONS =====
    
    /**
     * Lấy danh sách tỉnh/thành phố
     * @returns {Promise<Array>} Mảng các tỉnh/thành phố
     */
    async function fetchProvinces() {
        try {
            const response = await fetch(API_PROVINCES);
            if (!response.ok) throw new Error('Không thể tải danh sách tỉnh/thành phố');
            
            const data = await response.json();
            provincesData = data;
            return data;
        } catch (error) {
            console.error('Lỗi khi tải tỉnh/thành phố:', error);
            showToast('Không thể tải danh sách tỉnh/thành phố. Vui lòng làm mới trang và thử lại.', 'error');
            return [];
        }
    }
    
    /**
     * Lấy danh sách quận/huyện theo tỉnh/thành phố
     * @param {string} provinceCode Mã tỉnh/thành phố
     * @returns {Promise<Array>} Mảng các quận/huyện
     */
    async function fetchDistricts(provinceCode) {
        // Kiểm tra cache trước
        if (districtsCache[provinceCode]) {
            return districtsCache[provinceCode];
        }
        
        try {
            const url = API_DISTRICTS.replace('{province_code}', provinceCode);
            const response = await fetch(url);
            if (!response.ok) throw new Error('Không thể tải danh sách quận/huyện');
            
            const data = await response.json();
            const districts = data.districts || [];
            
            // Lưu vào cache
            districtsCache[provinceCode] = districts;
            
            return districts;
        } catch (error) {
            console.error('Lỗi khi tải quận/huyện:', error);
            showToast('Không thể tải danh sách quận/huyện. Vui lòng thử lại.', 'error');
            return [];
        }
    }
    
    /**
     * Lấy danh sách phường/xã theo quận/huyện
     * @param {string} districtCode Mã quận/huyện
     * @returns {Promise<Array>} Mảng các phường/xã
     */
    async function fetchWards(districtCode) {
        // Kiểm tra cache trước
        if (wardsCache[districtCode]) {
            return wardsCache[districtCode];
        }
        
        try {
            const url = API_WARDS.replace('{district_code}', districtCode);
            const response = await fetch(url);
            if (!response.ok) throw new Error('Không thể tải danh sách phường/xã');
            
            const data = await response.json();
            const wards = data.wards || [];
            
            // Lưu vào cache
            wardsCache[districtCode] = wards;
            
            return wards;
        } catch (error) {
            console.error('Lỗi khi tải phường/xã:', error);
            showToast('Không thể tải danh sách phường/xã. Vui lòng thử lại.', 'error');
            return [];
        }
    }
    
    // ===== HELPER FUNCTIONS =====
    
    /**
     * Hiển thị thông báo toast
     * @param {string} message Nội dung thông báo
     * @param {string} type Loại thông báo (success, error, info, warning)
     */
    function showToast(message, type = 'info') {
        // Tạo element thông báo
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        // HTML nội bên trong
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Tạo container nếu chưa có
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        // Thêm toast vào container
        toastContainer.appendChild(toast);
        
        // Khởi tạo bootstrap toast
        const bsToast = new bootstrap.Toast(toast, {
            delay: 5000, // Tự động đóng sau 5 giây
            autohide: true
        });
        
        // Hiển thị toast
        bsToast.show();
        
        // Xóa toast khi đóng
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    }
    
    /**
     * Cập nhật options cho select element
     * @param {HTMLSelectElement} selectElement Element select cần cập nhật
     * @param {Array} data Dữ liệu cho options
     * @param {string} valueKey Tên thuộc tính làm value
     * @param {string} textKey Tên thuộc tính làm text
     * @param {boolean} preserveSelected Giữ lại giá trị đã chọn hay không
     */
    function updateSelectOptions(selectElement, data, valueKey = 'code', textKey = 'name', preserveSelected = true) {
        if (!selectElement) return;
        
        // Lưu giá trị đã chọn
        const selectedValue = preserveSelected ? selectElement.value : '';
        
        // Xóa tất cả options trừ option đầu tiên
        while (selectElement.options.length > 1) {
            selectElement.remove(1);
        }
        
        // Thêm options mới
        data.forEach(item => {
            const option = document.createElement('option');
            option.value = item[valueKey];
            option.textContent = item[textKey];
            selectElement.appendChild(option);
        });
        
        // Khôi phục giá trị đã chọn nếu có
        if (selectedValue && selectElement.querySelector(`option[value="${selectedValue}"]`)) {
            selectElement.value = selectedValue;
        }
        
        // Cập nhật select2 nếu đang sử dụng
        if ($(selectElement).data('select2')) {
            $(selectElement).trigger('change');
        }
    }
    
    /**
     * Hiển thị loading state cho select
     * @param {HTMLSelectElement} selectElement Element select
     * @param {boolean} isLoading Đang loading hay không
     */
    function setSelectLoading(selectElement, isLoading) {
        if (!selectElement) return;
        
        if (isLoading) {
            selectElement.disabled = true;
            selectElement.parentElement.classList.add('select-loading');
        } else {
            selectElement.disabled = false;
            selectElement.parentElement.classList.remove('select-loading');
        }
    }
    
    // ===== INITIALIZATION FUNCTIONS =====
    
    /**
     * Khởi tạo select tỉnh/thành phố
     * @param {HTMLSelectElement} selectElement Element select
     * @param {function} onChangeCallback Callback khi select thay đổi
     */
    async function initProvinceSelect(selectElement, onChangeCallback) {
        if (!selectElement) return;
        
        // Hiển thị loading
        setSelectLoading(selectElement, true);
        
        // Lấy dữ liệu tỉnh/thành phố nếu chưa có
        if (!provincesData.length) {
            provincesData = await fetchProvinces();
        }
        
        // Cập nhật options
        updateSelectOptions(selectElement, provincesData);
        
        // Xóa loading
        setSelectLoading(selectElement, false);
        
        // Đăng ký sự kiện change
        if (onChangeCallback) {
            selectElement.addEventListener('change', onChangeCallback);
        }
    }
    
    /**
     * Khởi tạo select quận/huyện
     * @param {HTMLSelectElement} provinceSelect Element select tỉnh/thành
     * @param {HTMLSelectElement} districtSelect Element select quận/huyện
     * @param {HTMLSelectElement} wardSelect Element select phường/xã
     */
    function initDistrictSelect(provinceSelect, districtSelect, wardSelect) {
        if (!provinceSelect || !districtSelect) return;
        
        provinceSelect.addEventListener('change', async function() {
            const provinceCode = this.value;
            
            // Reset select quận/huyện
            districtSelect.innerHTML = '<option value="">-- Chọn Quận/Huyện --</option>';
            if ($(districtSelect).data('select2')) {
                $(districtSelect).trigger('change');
            }
            
            // Reset select phường/xã nếu có
            if (wardSelect) {
                wardSelect.innerHTML = '<option value="">-- Chọn Phường/Xã --</option>';
                if ($(wardSelect).data('select2')) {
                    $(wardSelect).trigger('change');
                }
            }
            
            if (!provinceCode) return;
            
            // Hiển thị loading
            setSelectLoading(districtSelect, true);
            
            // Lấy dữ liệu quận/huyện
            const districts = await fetchDistricts(provinceCode);
            
            // Cập nhật options
            updateSelectOptions(districtSelect, districts, 'code', 'name', false);
            
            // Xóa loading
            setSelectLoading(districtSelect, false);
        });
    }
    
    /**
     * Khởi tạo select phường/xã
     * @param {HTMLSelectElement} districtSelect Element select quận/huyện
     * @param {HTMLSelectElement} wardSelect Element select phường/xã
     */
    function initWardSelect(districtSelect, wardSelect) {
        if (!districtSelect || !wardSelect) return;
        
        districtSelect.addEventListener('change', async function() {
            const districtCode = this.value;
            
            // Reset select phường/xã
            wardSelect.innerHTML = '<option value="">-- Chọn Phường/Xã --</option>';
            if ($(wardSelect).data('select2')) {
                $(wardSelect).trigger('change');
            }
            
            if (!districtCode) return;
            
            // Hiển thị loading
            setSelectLoading(wardSelect, true);
            
            // Lấy dữ liệu phường/xã
            const wards = await fetchWards(districtCode);
            
            // Cập nhật options
            updateSelectOptions(wardSelect, wards, 'code', 'name', false);
            
            // Xóa loading
            setSelectLoading(wardSelect, false);
        });
    }
    
    /**
     * Tạo và thêm nút sao chép từ địa chỉ quê quán
     */
    function createCopyAddressButton() {
        if (!addressCopyContainer) return;
        
        // Tạo nút
        const copyButton = document.createElement('button');
        copyButton.type = 'button';
        copyButton.className = 'btn btn-outline-secondary btn-sm mb-3';
        copyButton.innerHTML = '<i class="fas fa-copy me-1"></i> Sao chép từ địa chỉ quê quán';
        
        // Thêm vào container
        addressCopyContainer.appendChild(copyButton);
        
        // Thêm sự kiện click
        copyButton.addEventListener('click', async function() {
            // Kiểm tra đã chọn đủ thông tin quê quán chưa
            if (!hometownProvince.value) {
                showToast('Vui lòng chọn Tỉnh/Thành phố quê quán trước khi sao chép', 'warning');
                return;
            }
            
            // Hiển thị loading ở nút
            copyButton.disabled = true;
            copyButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Đang sao chép...';
            
            try {
                // Sao chép tỉnh/thành
                currentProvince.value = hometownProvince.value;
                
                // Trigger change để load quận/huyện
                if ($(currentProvince).data('select2')) {
                    $(currentProvince).trigger('change');
                } else {
                    currentProvince.dispatchEvent(new Event('change'));
                }
                
                // Đợi load quận/huyện
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // Sao chép quận/huyện nếu có
                if (hometownDistrict.value && currentDistrict) {
                    currentDistrict.value = hometownDistrict.value;
                    
                    // Trigger change để load phường/xã
                    if ($(currentDistrict).data('select2')) {
                        $(currentDistrict).trigger('change');
                    } else {
                        currentDistrict.dispatchEvent(new Event('change'));
                    }
                    
                    // Đợi load phường/xã
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    // Sao chép phường/xã nếu có
                    if (hometownWard.value && currentWard) {
                        currentWard.value = hometownWard.value;
                        
                        if ($(currentWard).data('select2')) {
                            $(currentWard).trigger('change');
                        }
                    }
                }
                
                // Sao chép địa chỉ chi tiết
                if (hometownAddress.value && currentAddress) {
                    currentAddress.value = hometownAddress.value;
                }
                
                showToast('Đã sao chép địa chỉ thành công', 'success');
            } catch (error) {
                console.error('Lỗi khi sao chép địa chỉ:', error);
                showToast('Không thể sao chép địa chỉ. Vui lòng thử lại.', 'error');
            } finally {
                // Khôi phục nút
                copyButton.disabled = false;
                copyButton.innerHTML = '<i class="fas fa-copy me-1"></i> Sao chép từ địa chỉ quê quán';
            }
        });
    }
    
    // ===== INIT APPLICATION =====
    
    /**
     * Khởi tạo tất cả các thành phần
     */
    async function initializeAddressSelects() {
        try {
            // 1. Lấy dữ liệu tỉnh/thành phố
            const provinces = await fetchProvinces();
            if (!provinces.length) {
                showToast('Không thể tải danh sách địa chỉ. Một số chức năng có thể không hoạt động.', 'warning');
                return;
            }
            
            // 2. Khởi tạo select nơi cấp CMND/CCCD
            if (idCardIssuePlace) {
                updateSelectOptions(idCardIssuePlace, provinces);
            }
            
            // 3. Khởi tạo select tỉnh/thành phố quê quán
            if (hometownProvince) {
                updateSelectOptions(hometownProvince, provinces);
                
                // Khởi tạo select quận/huyện và phường/xã quê quán
                initDistrictSelect(hometownProvince, hometownDistrict, hometownWard);
                initWardSelect(hometownDistrict, hometownWard);
            }
            
            // 4. Khởi tạo select tỉnh/thành phố hiện tại
            if (currentProvince) {
                updateSelectOptions(currentProvince, provinces);
                
                // Khởi tạo select quận/huyện và phường/xã hiện tại
                initDistrictSelect(currentProvince, currentDistrict, currentWard);
                initWardSelect(currentDistrict, currentWard);
            }
            
            // 5. Tạo nút sao chép địa chỉ
            createCopyAddressButton();
            
        } catch (error) {
            console.error('Lỗi khởi tạo select địa chỉ:', error);
            showToast('Đã xảy ra lỗi khi khởi tạo thông tin địa chỉ. Vui lòng tải lại trang.', 'error');
        }
    }
    
    // Khởi tạo khi trang được tải xong
    initializeAddressSelects();
    
    // Hiển thị thông báo khi API địa chỉ không khả dụng
    window.addEventListener('error', function(e) {
        if (e.target.tagName === 'SCRIPT' && e.target.src.includes('provinces.open-api.vn')) {
            showToast('Không thể kết nối đến API địa chỉ. Vui lòng kiểm tra kết nối internet.', 'error');
        }
    }, true);
    
    // ===== CSS TRONG JAVASCRIPT =====
    // Thêm các style cần thiết nếu chưa có trong CSS
    const styleElement = document.createElement('style');
    styleElement.textContent = `
        /* Loading indicator cho select */
        .select-loading .select2-selection__arrow {
            display: none;
        }
        
        .select-loading::after {
            content: "";
            width: 16px;
            height: 16px;
            border: 2px solid rgba(0, 0, 0, 0.1);
            border-top: 2px solid #3b7ddd;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            position: absolute;
            top: 50%;
            right: 10px;
            transform: translateY(-50%);
        }
        
        @keyframes spin {
            0% { transform: translateY(-50%) rotate(0deg); }
            100% { transform: translateY(-50%) rotate(360deg); }
        }
        
        /* Styling cho toast notification */
        .toast-container {
            z-index: 9999;
        }
    `;
    document.head.appendChild(styleElement);

    // Document upload handlers
    initializeDocumentUploads();
    
    // Form validation
    initializeFormValidation();
});

/**
 * Initialize document upload functionality
 */
function initializeDocumentUploads() {
    // Handle custom file uploads
    const uploadContainers = document.querySelectorAll('.custom-file-upload');
    
    uploadContainers.forEach(container => {
        const input = container.querySelector('input[type="file"]');
        if (!input) return;
        
        // Add click event to the container
        container.addEventListener('click', function() {
            input.click();
        });
        
        // Handle file selection
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;
            
            // Update UI to show selected file
            const icon = container.querySelector('i');
            const text = container.querySelector('p');
            
            // Change icon based on file type
            if (file.type.startsWith('image/')) {
                icon.className = 'fas fa-image';
            } else if (file.type === 'application/pdf') {
                icon.className = 'fas fa-file-pdf';
            } else {
                icon.className = 'fas fa-file';
            }
            
            // Update text
            text.textContent = file.name;
            
            // Add visual indicator for selected file
            container.classList.add('file-selected');
            
            // Create preview for images
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    // Check if preview already exists
                    let preview = container.parentNode.querySelector('.file-preview');
                    
                    if (!preview) {
                        // Create preview element
                        preview = document.createElement('div');
                        preview.className = 'file-preview mt-2';
                        container.parentNode.appendChild(preview);
                    }
                    
                    preview.innerHTML = `
                        <div class="position-relative">
                            <img src="${e.target.result}" class="img-thumbnail" style="max-height: 150px">
                            <button type="button" class="btn btn-sm btn-danger position-absolute top-0 end-0 remove-preview" 
                                    title="Remove file">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    `;
                    
                    // Add remove button functionality
                    const removeBtn = preview.querySelector('.remove-preview');
                    removeBtn.addEventListener('click', function(evt) {
                        evt.stopPropagation(); // Prevent triggering container click
                        
                        // Reset file input
                        input.value = '';
                        
                        // Reset UI
                        if (container.id === 'id-card-front') {
                            icon.className = 'fas fa-id-card';
                            text.textContent = 'Nhấp để tải lên mặt trước CMND/CCCD';
                        } else if (container.id === 'id-card-back') {
                            icon.className = 'fas fa-id-card';
                            text.textContent = 'Nhấp để tải lên mặt sau CMND/CCCD';
                        } else if (container.id === 'diploma-upload') {
                            icon.className = 'fas fa-graduation-cap';
                            text.textContent = 'Nhấp để tải lên bằng cấp';
                        } else if (container.id === 'other-docs') {
                            icon.className = 'fas fa-file-alt';
                            text.textContent = 'Nhấp để tải lên các tài liệu khác';
                        }
                        
                        container.classList.remove('file-selected');
                        preview.remove();
                    });
                };
                reader.readAsDataURL(file);
            } else {
                // For non-image files, show file type icon and name
                let preview = container.parentNode.querySelector('.file-preview');
                
                if (!preview) {
                    preview = document.createElement('div');
                    preview.className = 'file-preview mt-2';
                    container.parentNode.appendChild(preview);
                }
                
                let fileIcon = 'fa-file';
                if (file.type === 'application/pdf') {
                    fileIcon = 'fa-file-pdf';
                } else if (file.name.endsWith('.doc') || file.name.endsWith('.docx')) {
                    fileIcon = 'fa-file-word';
                } else if (file.name.endsWith('.xls') || file.name.endsWith('.xlsx')) {
                    fileIcon = 'fa-file-excel';
                }
                
                preview.innerHTML = `
                    <div class="d-flex align-items-center p-2 bg-light rounded">
                        <i class="fas ${fileIcon} fa-2x text-primary me-2"></i>
                        <div class="text-truncate">${file.name}</div>
                        <button type="button" class="btn btn-sm btn-link text-danger ms-auto remove-preview" 
                                title="Remove file">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `;
                
                // Add remove button functionality
                const removeBtn = preview.querySelector('.remove-preview');
                removeBtn.addEventListener('click', function(evt) {
                    evt.stopPropagation(); // Prevent triggering container click
                    
                    // Reset file input
                    input.value = '';
                    
                    // Reset UI
                    if (container.id === 'id-card-front') {
                        icon.className = 'fas fa-id-card';
                        text.textContent = 'Nhấp để tải lên mặt trước CMND/CCCD';
                    } else if (container.id === 'id-card-back') {
                        icon.className = 'fas fa-id-card';
                        text.textContent = 'Nhấp để tải lên mặt sau CMND/CCCD';
                    } else if (container.id === 'diploma-upload') {
                        icon.className = 'fas fa-graduation-cap';
                        text.textContent = 'Nhấp để tải lên bằng cấp';
                    } else if (container.id === 'other-docs') {
                        icon.className = 'fas fa-file-alt';
                        text.textContent = 'Nhấp để tải lên các tài liệu khác';
                    }
                    
                    container.classList.remove('file-selected');
                    preview.remove();
                });
            }
        });
    });
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    const form = document.getElementById('employee-form');
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        // Reset previous validation errors
        clearValidationErrors();
        
        // Get all required fields
        const requiredFields = form.querySelectorAll('[required]');
        let hasErrors = false;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                e.preventDefault();
                hasErrors = true;
                showFieldError(field, 'This field is required.');
            }
        });
        
        // Email validation
        const emailField = form.querySelector('#id_email');
        if (emailField && emailField.value.trim()) {
            const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailPattern.test(emailField.value.trim())) {
                e.preventDefault();
                hasErrors = true;
                showFieldError(emailField, 'Please enter a valid email address.');
            }
        }
        
        // Phone validation
        const phoneField = form.querySelector('#id_phone');
        if (phoneField && phoneField.value.trim()) {
            const phonePattern = /^\d{10,15}$/;
            if (!phonePattern.test(phoneField.value.replace(/[\s()-]/g, ''))) {
                e.preventDefault();
                hasErrors = true;
                showFieldError(phoneField, 'Please enter a valid phone number.');
            }
        }
        
        // ID card validation
        const idCardField = form.querySelector('#id_id_card');
        if (idCardField && idCardField.value.trim()) {
            const idCardPattern = /^[\d]{9,12}$/;
            if (!idCardPattern.test(idCardField.value.replace(/[\s.-]/g, ''))) {
                e.preventDefault();
                hasErrors = true;
                showFieldError(idCardField, 'Please enter a valid ID card number (9-12 digits).');
            }
        }
        
        // Show form error message if validation fails
        if (hasErrors) {
            // Create an error summary at the top of the form
            const errorSummary = document.createElement('div');
            errorSummary.className = 'alert alert-danger';
            errorSummary.innerHTML = '<strong>Please correct the following errors:</strong><ul class="mb-0 pl-4"></ul>';
            
            const errorList = errorSummary.querySelector('ul');
            document.querySelectorAll('.field-error').forEach(error => {
                const li = document.createElement('li');
                li.textContent = error.textContent;
                errorList.appendChild(li);
            });
            
            form.prepend(errorSummary);
            
            // Scroll to the first error
            const firstErrorField = form.querySelector('.is-invalid');
            if (firstErrorField) {
                firstErrorField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstErrorField.focus();
            }
        }
    });
    
    // Add validation feedback on field blur
    const validatableFields = form.querySelectorAll('input, select, textarea');
    validatableFields.forEach(field => {
        field.addEventListener('blur', function() {
            if (field.hasAttribute('required') && !field.value.trim()) {
                showFieldError(field, 'This field is required.');
            } else {
                clearFieldError(field);
            }
            
            // Specific field validations
            if (field.id === 'id_email' && field.value.trim()) {
                const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailPattern.test(field.value.trim())) {
                    showFieldError(field, 'Please enter a valid email address.');
                }
            }
            
            if (field.id === 'id_phone' && field.value.trim()) {
                const phonePattern = /^\d{10,15}$/;
                if (!phonePattern.test(field.value.replace(/[\s()-]/g, ''))) {
                    showFieldError(field, 'Please enter a valid phone number.');
                }
            }
        });
        
        // Clear error when field is edited
        field.addEventListener('input', function() {
            clearFieldError(field);
        });
    });
    
    /**
     * Show error message for a field
     */
    function showFieldError(field, message) {
        // Add invalid class
        field.classList.add('is-invalid');
        
        // Check if error message already exists
        let errorElement = field.parentNode.querySelector('.field-error');
        
        if (!errorElement) {
            // Create error message
            errorElement = document.createElement('div');
            errorElement.className = 'invalid-feedback field-error';
            errorElement.textContent = message;
            
            // Add error after the field
            field.parentNode.appendChild(errorElement);
        }
    }
    
    /**
     * Clear error message for a field
     */
    function clearFieldError(field) {
        field.classList.remove('is-invalid');
        
        const errorElement = field.parentNode.querySelector('.field-error');
        if (errorElement) {
            errorElement.remove();
        }
    }
    
    /**
     * Clear all validation errors
     */
    function clearValidationErrors() {
        // Remove error summary
        const errorSummary = form.querySelector('.alert-danger');
        if (errorSummary) {
            errorSummary.remove();
        }
        
        // Remove field errors
        form.querySelectorAll('.is-invalid').forEach(field => {
            clearFieldError(field);
        });
    }
}

// Add CSS for file upload styling
const style = document.createElement('style');
style.textContent = `
.custom-file-upload {
    border: 2px dashed #ddd;
    border-radius: 5px;
    padding: 20px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s;
}

.custom-file-upload:hover {
    border-color: #6c757d;
    background-color: rgba(0,0,0,0.01);
}

.custom-file-upload i {
    font-size: 24px;
    color: #6c757d;
    margin-bottom: 10px;
}

.custom-file-upload.file-selected {
    border-color: #28a745;
    background-color: rgba(40, 167, 69, 0.05);
}

.custom-file-upload.file-selected i {
    color: #28a745;
}

.file-preview {
    transition: all 0.3s;
}

.remove-preview {
    opacity: 0.7;
}

.remove-preview:hover {
    opacity: 1;
}
`;
document.head.appendChild(style);
