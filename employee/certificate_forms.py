from django import forms
from django.core.exceptions import ValidationError
from .models import CertificateType, EmployeeCertificate
from datetime import date

class CertificateTypeForm(forms.ModelForm):
    """Form for creating and managing certificate types"""
    class Meta:
        model = CertificateType
        fields = ['type_name', 'description', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class EmployeeCertificateForm(forms.ModelForm):
    """Form for managing employee certificates"""
    class Meta:
        model = EmployeeCertificate
        fields = ['type', 'certificate_name', 'issued_by', 'issued_date', 
                 'expiry_date', 'certificate_number', 'attachment_file', 'notes']
        widgets = {
            'issued_date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        issued_date = cleaned_data.get('issued_date')
        expiry_date = cleaned_data.get('expiry_date')
        
        if issued_date and expiry_date and issued_date > expiry_date:
            self.add_error('expiry_date', 'Expiry date must be after issue date')
        
        # Determine status based on expiry date
        if expiry_date:
            if expiry_date < date.today():
                cleaned_data['status'] = 'Expired'
            else:
                cleaned_data['status'] = 'Valid'
        
        return cleaned_data