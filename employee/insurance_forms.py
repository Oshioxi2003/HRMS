from django import forms
from django.core.exceptions import ValidationError
from .models import InsuranceAndTax

class InsuranceAndTaxForm(forms.ModelForm):
    """Form for managing employee insurance and tax information"""
    class Meta:
        model = InsuranceAndTax
        fields = ['social_insurance_number', 'social_insurance_date', 
                  'social_insurance_place', 'health_insurance_number', 
                  'health_insurance_date', 'health_insurance_place', 
                  'health_care_provider', 'tax_code', 'status']
        widgets = {
            'social_insurance_date': forms.DateInput(attrs={'type': 'date'}),
            'health_insurance_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def clean_social_insurance_number(self):
        number = self.cleaned_data.get('social_insurance_number')
        if number:
            # Simple validation for insurance number format (can be customized)
            if len(number) < 8:
                raise ValidationError('Social insurance number must be at least 8 characters')
        
        return number
    
    def clean_tax_code(self):
        tax_code = self.cleaned_data.get('tax_code')
        if tax_code:
            # Basic tax code validation (customize as needed)
            if len(tax_code) < 10:
                raise ValidationError('Tax code should be at least 10 characters')
        
        return tax_code