from django.db import models
from django.contrib.auth import get_user_model
from employee.models import Employee, Department

User = get_user_model()

class DocumentCategory(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.category_name

class Document(models.Model):
    VISIBILITY_CHOICES = (
        ('Private', 'Riêng tư'),
        ('Department', 'Phòng ban'),
        ('Company', 'Công ty'),
    )
    
    document_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(DocumentCategory, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='documents/')
    file_type = models.CharField(max_length=50, null=True, blank=True)
    file_size = models.IntegerField(default=0)  # Kích thước tính bằng KB
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='Private')
    version = models.CharField(max_length=20, null=True, blank=True)
    tags = models.CharField(max_length=200, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def filename(self):
        return self.file.name.split('/')[-1]
    
    def get_file_icon(self):
        """Trả về biểu tượng thích hợp dựa trên loại tệp"""
        file_type = self.file_type.lower() if self.file_type else ''
        
        if 'pdf' in file_type:
            return 'far fa-file-pdf'
        elif 'word' in file_type or 'doc' in file_type:
            return 'far fa-file-word'
        elif 'excel' in file_type or 'sheet' in file_type or 'csv' in file_type:
            return 'far fa-file-excel'
        elif 'powerpoint' in file_type or 'presentation' in file_type:
            return 'far fa-file-powerpoint'
        elif 'image' in file_type or 'jpg' in file_type or 'png' in file_type:
            return 'far fa-file-image'
        elif 'zip' in file_type or 'compressed' in file_type:
            return 'far fa-file-archive'
        elif 'text' in file_type:
            return 'far fa-file-alt'
        else:
            return 'far fa-file'
