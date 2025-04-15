from django import forms
from django.core.exceptions import ValidationError
from .models import *
from employee.models import Employee
from datetime import date

class EmploymentContractForm(forms.ModelForm):
    """Form for managing employment contracts"""
    class Meta:
        model = EmploymentContract
        fields = ['employee', 'contract_type', 'start_date', 'end_date', 
                  'base_salary', 'allowance', 'attached_file', 'sign_date', 
                  'signed_by', 'notes', 'status']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'sign_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        contract_type = cleaned_data.get('contract_type')
        employee = cleaned_data.get('employee')
        
        if contract_type != 'Indefinite-term' and not end_date:
            self.add_error('end_date', 'End date is required for this contract type')
        
        if start_date and end_date and start_date > end_date:
            self.add_error('end_date', 'End date must be after start date')
        
        # Check for overlapping active contracts for the same employee
        if employee and start_date:
            existing_query = EmploymentContract.objects.filter(
                employee=employee,
                status='Active'
            )
            
            if end_date:
                # Check for overlap
                existing_query = existing_query.filter(
                    start_date__lte=end_date,
                    end_date__gte=start_date
                ) | existing_query.filter(
                    start_date__lte=end_date,
                    end_date__isnull=True
                )
            else:
                # No end date for new contract (indefinite), check any future contracts
                existing_query = existing_query.filter(
                    end_date__gte=start_date
                ) | existing_query.filter(
                    end_date__isnull=True
                )
            
            # Exclude current instance if updating
            if self.instance.pk:
                existing_query = existing_query.exclude(pk=self.instance.pk)
            
            if existing_query.exists():
                self.add_error('start_date', 
                    'There is an overlapping active contract for this employee')
        
        return cleaned_data

class ContractTerminationForm(forms.Form):
    """Form for terminating a contract"""
    termination_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=date.today
    )
    termination_reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=True
    )
    
    def clean_termination_date(self):
        termination_date = self.cleaned_data.get('termination_date')
        if termination_date and termination_date > date.today():
            raise ValidationError('Termination date cannot be in the future')
        return termination_date

class ContractRenewalForm(forms.Form):
    """Form for renewing a contract"""
    new_start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    new_end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        help_text='Leave blank for indefinite-term contracts'
    )
    new_contract_type = forms.ChoiceField(
        choices=EmploymentContract.CONTRACT_TYPE_CHOICES
    )
    new_base_salary = forms.DecimalField(
        max_digits=15, decimal_places=2,
        min_value=0
    )
    new_allowance = forms.DecimalField(
        max_digits=15, decimal_places=2,
        min_value=0,
        required=False,
        initial=0
    )
    renewal_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_start_date = cleaned_data.get('new_start_date')
        new_end_date = cleaned_data.get('new_end_date')
        new_contract_type = cleaned_data.get('new_contract_type')
        
        if new_contract_type != 'Indefinite-term' and not new_end_date:
            self.add_error('new_end_date', 'End date is required for this contract type')
        
        if new_start_date and new_end_date and new_start_date > new_end_date:
            self.add_error('new_end_date', 'End date must be after start date')
        
        return cleaned_data