from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import DocumentCategory, Document
import os

class DocumentCategoryForm(forms.ModelForm):
    """Form để tạo và quản lý danh mục tài liệu"""
    class Meta:
        model = DocumentCategory
        fields = ['category_name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class DocumentForm(forms.ModelForm):
    """Form để tải lên và quản lý tài liệu"""
    class Meta:
        model = Document
        fields = ['title', 'description', 'category', 'file', 'department',
                 'employee', 'visibility', 'version', 'tags']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'tags': forms.TextInput(attrs={'placeholder': 'Nhập thẻ phân cách bằng dấu phẩy'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Nếu có user, thiết lập giá trị mặc định
        if user:
            if user.employee:
                self.fields['employee'].initial = user.employee
                if user.employee.department:
                    self.fields['department'].initial = user.employee.department
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Kiểm tra kích thước tệp (tối đa 20MB)
            if file.size > 20 * 1024 * 1024:
                raise ValidationError(_('Kích thước tệp không được vượt quá 20MB'))
            
            # Kiểm tra phần mở rộng tệp
            ext = os.path.splitext(file.name)[1].lower()
            valid_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', 
                              '.txt', '.csv', '.jpg', '.jpeg', '.png', '.zip']
            
            if ext not in valid_extensions:
                raise ValidationError(_('Phần mở rộng tệp không được hỗ trợ. Các loại cho phép: PDF, tài liệu Office, hình ảnh, ZIP.'))
            
            # Thiết lập loại tệp dựa trên phần mở rộng
            file_type_map = {
                '.pdf': 'application/pdf',
                '.doc': 'application/msword',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.xls': 'application/vnd.ms-excel',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                '.ppt': 'application/vnd.ms-powerpoint',
                '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                '.txt': 'text/plain',
                '.csv': 'text/csv',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.zip': 'application/zip'
            }
            
            self.instance.file_type = file_type_map.get(ext, 'application/octet-stream')
            
            # Thiết lập kích thước tệp tính bằng KB
            self.instance.file_size = file.size // 1024
        
        return file
