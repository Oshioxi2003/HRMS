from django import forms
from .models import AssetCategory, Asset, AssetAssignment, AssetRequest, AssetMaintenance
from employee.models import Employee

class AssetCategoryForm(forms.ModelForm):
    class Meta:
        model = AssetCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].widget.attrs.update({'class': 'form-control'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})

class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'asset_tag', 'asset_name', 'category', 'description', 
            'serial_number', 'model_number', 'purchase_date', 
            'purchase_cost', 'warranty_expiry', 'location', 
            'status', 'condition', 'notes'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
            'warranty_expiry': forms.DateInput(attrs={'type': 'date'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Chỉ hiển thị các danh mục đang hoạt động
        self.fields['category'].queryset = AssetCategory.objects.filter(is_active=True)
        
        # Thêm class form-control cho tất cả các trường
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.Select, forms.NumberInput, forms.DateInput, forms.Textarea)):
                field.widget.attrs.update({'class': 'form-control'})

class AssetAssignmentForm(forms.ModelForm):
    class Meta:
        model = AssetAssignment
        fields = [
            'employee', 'assignment_date', 'expected_return_date', 
            'assignment_notes'
        ]
        widgets = {
            'assignment_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_return_date': forms.DateInput(attrs={'type': 'date'}),
            'assignment_notes': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sắp xếp nhân viên theo tên
        self.fields['employee'].queryset = Employee.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        # Thêm class form-control cho tất cả các trường
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.Select, forms.DateInput, forms.Textarea)):
                field.widget.attrs.update({'class': 'form-control'})

class AssetReturnForm(forms.ModelForm):
    class Meta:
        model = AssetAssignment
        fields = ['return_condition', 'return_notes']
        widgets = {
            'return_notes': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Thêm class form-control cho tất cả các trường
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.Select, forms.Textarea)):
                field.widget.attrs.update({'class': 'form-control'})

class AssetRequestForm(forms.ModelForm):
    class Meta:
        model = AssetRequest
        fields = [
            'category', 'asset_name', 'description', 'reason',
            'needed_from', 'needed_until'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'reason': forms.Textarea(attrs={'rows': 3}),
            'needed_from': forms.DateInput(attrs={'type': 'date'}),
            'needed_until': forms.DateInput(attrs={'type': 'date'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Chỉ hiển thị các danh mục đang hoạt động
        self.fields['category'].queryset = AssetCategory.objects.filter(is_active=True)
        
        # Thêm class form-control cho tất cả các trường
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.Select, forms.DateInput, forms.Textarea)):
                field.widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        cleaned_data = super().clean()
        needed_from = cleaned_data.get('needed_from')
        needed_until = cleaned_data.get('needed_until')
        
        if needed_from and needed_until and needed_from > needed_until:
            raise forms.ValidationError("Ngày bắt đầu cần không thể sau ngày kết thúc.")
        
        return cleaned_data

class AssetRequestApprovalForm(forms.ModelForm):
    class Meta:
        model = AssetRequest
        fields = ['status', 'rejection_reason', 'fulfilled_with']
        widgets = {
            'rejection_reason': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Giới hạn trạng thái có thể chọn
        self.fields['status'].choices = [
            ('Approved', 'Approved'),
            ('Rejected', 'Rejected'),
            ('Fulfilled', 'Fulfilled')
        ]
        
        # Chỉ hiển thị các tài sản có sẵn
        self.fields['fulfilled_with'].queryset = Asset.objects.filter(status='Available')
        self.fields['fulfilled_with'].required = False
        
        # Thêm class form-control cho tất cả các trường
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.Select, forms.Textarea)):
                field.widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        rejection_reason = cleaned_data.get('rejection_reason')
        fulfilled_with = cleaned_data.get('fulfilled_with')
        
        if status == 'Rejected' and not rejection_reason:
            raise forms.ValidationError("Vui lòng cung cấp lý do từ chối.")
        
        if status == 'Fulfilled' and not fulfilled_with:
            raise forms.ValidationError("Vui lòng chọn tài sản để cấp phát.")
        
        return cleaned_data

class AssetMaintenanceForm(forms.ModelForm):
    class Meta:
        model = AssetMaintenance
        fields = [
            'maintenance_type', 'start_date', 'end_date', 
            'cost', 'provider', 'details', 'status'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'details': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Thêm class form-control cho tất cả các trường
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.Select, forms.NumberInput, forms.DateInput, forms.Textarea)):
                field.widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Ngày bắt đầu không thể sau ngày kết thúc.")
        
        return cleaned_data
