from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import date
from .models import (
    Employee, EmployeeLocation, Department, Position, AcademicTitle, 
    EducationLevel, InsuranceAndTax, CertificateType, EmployeeCertificate
)

class DepartmentForm(forms.ModelForm):
    """Form for creating and managing departments"""
    class Meta:
        model = Department
        fields = ['department_name', 'department_code', 'description', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'department_name': forms.TextInput(attrs={'class': 'form-control'}),
            'department_code': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_department_code(self):
        code = self.cleaned_data.get('department_code')
        if code:
            # Check if code exists for a different department
            existing_dept = Department.objects.filter(department_code=code)
            if self.instance.pk:
                existing_dept = existing_dept.exclude(pk=self.instance.pk)
            
            if existing_dept.exists():
                raise ValidationError(_('This department code is already in use'))
            
            # Ensure code follows pattern (uppercase letters and numbers)
            if not code.replace('-', '').isalnum() or not code.replace('-', '').isupper():
                raise ValidationError(_('Department code must contain only uppercase letters, numbers, and hyphens'))
        
        return code

class PositionForm(forms.ModelForm):
    """Form for creating and managing positions"""
    class Meta:
        model = Position
        fields = ['position_name', 'position_code', 'description', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'position_name': forms.TextInput(attrs={'class': 'form-control'}),
            'position_code': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_position_code(self):
        code = self.cleaned_data.get('position_code')
        if code:
            # Check if code exists for a different position
            existing_pos = Position.objects.filter(position_code=code)
            if self.instance.pk:
                existing_pos = existing_pos.exclude(pk=self.instance.pk)
            
            if existing_pos.exists():
                raise ValidationError(_('This position code is already in use'))
            
            # Ensure code follows pattern (uppercase letters and numbers)
            if not code.replace('-', '').isalnum() or not code.replace('-', '').isupper():
                raise ValidationError(_('Position code must contain only uppercase letters, numbers, and hyphens'))
        
        return code

class AcademicTitleForm(forms.ModelForm):
    """Form for creating and managing academic titles"""
    class Meta:
        model = AcademicTitle
        fields = ['title_name', 'title_code', 'description', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'title_name': forms.TextInput(attrs={'class': 'form-control'}),
            'title_code': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_title_code(self):
        code = self.cleaned_data.get('title_code')
        if code:
            # Check for duplicates
            existing = AcademicTitle.objects.filter(title_code=code)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError(_('This title code is already in use'))
        
        return code

class EducationLevelForm(forms.ModelForm):
    """Form for creating and managing education levels"""
    class Meta:
        model = EducationLevel
        fields = ['education_name', 'education_code', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'education_name': forms.TextInput(attrs={'class': 'form-control'}),
            'education_code': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_education_code(self):
        code = self.cleaned_data.get('education_code')
        if code:
            # Check for duplicates
            existing = EducationLevel.objects.filter(education_code=code)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError(_('This education code is already in use'))
        
        return code

class EmployeeForm(forms.ModelForm):
    """Form for complete employee management (HR use)"""
    
    # Add document upload fields
    id_card_front = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'd-none', 'accept': 'image/*,.pdf'}))
    id_card_back = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'd-none', 'accept': 'image/*,.pdf'}))
    diploma = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'd-none', 'accept': 'image/*,.pdf'}))
    other_documents = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'd-none', 'accept': 'image/*,.pdf'}))
    
    class Meta:
        model = Employee
        exclude = ['created_date', 'updated_date', 'approval_status', 'approval_date', 'approval_notes']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'required': 'required'}),
            'gender': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'id_card': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'id_card_issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'required': 'required'}),
            'id_card_issue_place': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': 'required'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'required': 'required'}),
            'department': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'position': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'education': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.Select(attrs={'class': 'form-select'}),
            'hire_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'required': 'required'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check if email exists for a different employee
            if Employee.objects.filter(email=email).exclude(pk=self.instance.pk if self.instance.pk else None).exists():
                raise ValidationError(_('This email is already in use by another employee.'))
        return email
    
    def clean_id_card(self):
        id_card = self.cleaned_data.get('id_card')
        if id_card:
            # Check if ID card exists for a different employee
            if Employee.objects.filter(id_card=id_card).exclude(pk=self.instance.pk if self.instance.pk else None).exists():
                raise ValidationError(_('This ID card number is already in use by another employee.'))
        return id_card
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            # Example validation: employee must be at least 18 years old
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 18:
                raise ValidationError(_('Employee must be at least 18 years old.'))
        return dob
    
    def clean(self):
        cleaned_data = super().clean()
        date_of_birth = cleaned_data.get('date_of_birth')
        hire_date = cleaned_data.get('hire_date')
        
        if date_of_birth and hire_date:
            if hire_date < date_of_birth:
                self.add_error('hire_date', _('Hire date cannot be before date of birth.'))
            
            # Calculate age at hire date
            age_at_hire = hire_date.year - date_of_birth.year - ((hire_date.month, hire_date.day) < (date_of_birth.month, date_of_birth.day))
            if age_at_hire < 18:
                self.add_error('hire_date', _('Employee must be at least 18 years old when hired.'))
        
        return cleaned_data

class EmployeeProfileForm(forms.ModelForm):
    """Simplified form for employee self-service"""
    class Meta:
        model = Employee
        fields = ['full_name', 'date_of_birth', 'gender', 'email', 'phone', 'address', 'profile_image']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check if email exists for a different employee
            if Employee.objects.filter(email=email).exclude(pk=self.instance.pk if self.instance.pk else None).exists():
                raise ValidationError(_('This email is already in use by another employee.'))
        return email

class EmployeeBasicInfoForm(forms.ModelForm):
    """Form for basic employee information (for quick creation)"""
    class Meta:
        model = Employee
        fields = ['full_name', 'date_of_birth', 'gender', 'email', 'phone', 'id_card', 'id_card_issue_date']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'id_card': forms.TextInput(attrs={'class': 'form-control'}),
            'id_card_issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            if Employee.objects.filter(email=email).exclude(pk=self.instance.pk if self.instance.pk else None).exists():
                raise ValidationError(_('This email is already in use by another employee.'))
        return email
    
    def clean_id_card(self):
        id_card = self.cleaned_data.get('id_card')
        if id_card:
            if Employee.objects.filter(id_card=id_card).exclude(pk=self.instance.pk if self.instance.pk else None).exists():
                raise ValidationError(_('This ID card number is already in use by another employee.'))
        return id_card

class EmployeeLocationForm(forms.ModelForm):
    """Form for employee location details"""
    class Meta:
        model = EmployeeLocation
        exclude = ['employee', 'created_date', 'updated_date']
        widgets = {
            'hometown_province': forms.TextInput(attrs={'class': 'form-control'}),
            'hometown_district': forms.TextInput(attrs={'class': 'form-control'}),
            'hometown_ward': forms.TextInput(attrs={'class': 'form-control'}),
            'hometown_address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'permanent_province': forms.TextInput(attrs={'class': 'form-control'}),
            'permanent_district': forms.TextInput(attrs={'class': 'form-control'}),
            'permanent_ward': forms.TextInput(attrs={'class': 'form-control'}),
            'permanent_address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'current_province': forms.TextInput(attrs={'class': 'form-control'}),
            'current_district': forms.TextInput(attrs={'class': 'form-control'}),
            'current_ward': forms.TextInput(attrs={'class': 'form-control'}),
            'current_address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

class InsuranceAndTaxForm(forms.ModelForm):
    """Form for insurance and tax information"""
    class Meta:
        model = InsuranceAndTax
        exclude = ['employee', 'created_date', 'updated_date']
        widgets = {
            'social_insurance_number': forms.TextInput(attrs={'class': 'form-control'}),
            'social_insurance_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'social_insurance_place': forms.TextInput(attrs={'class': 'form-control'}),
            'health_insurance_number': forms.TextInput(attrs={'class': 'form-control'}),
            'health_insurance_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'health_insurance_place': forms.TextInput(attrs={'class': 'form-control'}),
            'health_care_provider': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_code': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_social_insurance_number(self):
        number = self.cleaned_data.get('social_insurance_number')
        if number:
            # Example validation - adapt to your country's format
            if not number.isdigit() or len(number) < 8:
                raise ValidationError(_('Invalid social insurance number format.'))
        return number
    
    def clean_tax_code(self):
        code = self.cleaned_data.get('tax_code')
        if code:
            # Example validation - adapt to your country's format
            if not code.isalnum() or len(code) < 8:
                raise ValidationError(_('Invalid tax code format.'))
        return code

class CertificateTypeForm(forms.ModelForm):
    """Form for creating and managing certificate types"""
    class Meta:
        model = CertificateType
        fields = ['type_name', 'description', 'status']
        widgets = {
            'type_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'status': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class EmployeeCertificateForm(forms.ModelForm):
    """Form for managing employee certificates"""
    class Meta:
        model = EmployeeCertificate
        fields = ['type', 'certificate_name', 'issued_by', 'issued_date', 
                 'expiry_date', 'certificate_number', 'attachment_file', 'notes']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            'certificate_name': forms.TextInput(attrs={'class': 'form-control'}),
            'issued_by': forms.TextInput(attrs={'class': 'form-control'}),
            'issued_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'certificate_number': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        issued_date = cleaned_data.get('issued_date')
        expiry_date = cleaned_data.get('expiry_date')
        
        if issued_date and expiry_date and issued_date > expiry_date:
            self.add_error('expiry_date', _('Expiry date must be after issue date'))
        
        # Determine status based on expiry date
        if expiry_date:
            if expiry_date < date.today():
                cleaned_data['status'] = 'Expired'
            else:
                cleaned_data['status'] = 'Valid'
        
        return cleaned_data
