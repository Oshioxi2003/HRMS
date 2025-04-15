from django import forms
from django.core.exceptions import ValidationError
from .models import (SalaryGrade, SeniorityAllowance, EmployeeSalaryGrade, 
                    SalaryAdvance, Salary)
from employee.models import Employee
import calendar
from datetime import date

class SalaryGradeForm(forms.ModelForm):
    """Form for managing salary grades"""
    class Meta:
        model = SalaryGrade
        fields = ['grade_name', 'grade_code', 'base_salary_amount', 'description', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean_base_salary_amount(self):
        amount = self.cleaned_data.get('base_salary_amount')
        if amount and amount <= 0:
            raise ValidationError('Base salary amount must be greater than zero')
        return amount

class SeniorityAllowanceForm(forms.ModelForm):
    """Form for managing seniority allowances"""
    class Meta:
        model = SeniorityAllowance
        fields = ['years_of_service', 'allowance_percentage', 'description', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean_allowance_percentage(self):
        percentage = self.cleaned_data.get('allowance_percentage')
        if percentage and (percentage < 0 or percentage > 100):
            raise ValidationError('Allowance percentage must be between 0 and 100')
        return percentage

class EmployeeSalaryGradeForm(forms.ModelForm):
    """Form for assigning salary grades to employees"""
    class Meta:
        model = EmployeeSalaryGrade
        fields = ['employee', 'grade', 'effective_date', 'end_date', 
                  'decision_number', 'notes', 'status']
        widgets = {
            'effective_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        effective_date = cleaned_data.get('effective_date')
        end_date = cleaned_data.get('end_date')
        employee = cleaned_data.get('employee')
        
        if effective_date and end_date and end_date <= effective_date:
            self.add_error('end_date', 'End date must be after effective date')
        
        # Check if this would overlap with another active assignment
        if employee and effective_date:
            existing = EmployeeSalaryGrade.objects.filter(
                employee=employee,
                status='Active',
                effective_date__lte=effective_date,
                end_date__gte=effective_date
            )
            
            # Exclude current instance if updating
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                self.add_error('effective_date', 
                    'This overlaps with another active salary grade assignment')
        
        return cleaned_data

class SalaryAdvanceForm(forms.ModelForm):
    """Form for salary advance requests"""
    class Meta:
        model = SalaryAdvance
        fields = ['advance_date', 'amount', 'reason', 'deduction_month', 'deduction_year']
        widgets = {
            'advance_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError('Amount must be greater than zero')
        return amount
    
    def clean(self):
        cleaned_data = super().clean()
        deduction_month = cleaned_data.get('deduction_month')
        deduction_year = cleaned_data.get('deduction_year')
        
        # Validate month
        if deduction_month and (deduction_month < 1 or deduction_month > 12):
            self.add_error('deduction_month', 'Month must be between 1 and 12')
        
        # Validate future deduction
        if deduction_month and deduction_year:
            today = date.today()
            if (deduction_year < today.year or 
                (deduction_year == today.year and deduction_month < today.month)):
                self.add_error('deduction_month', 
                    'Deduction month/year must be in the future')
        
        return cleaned_data

class SalaryForm(forms.ModelForm):
    """Form for managing employee salaries"""
    class Meta:
        model = Salary
        fields = ['employee', 'month', 'year', 'work_days', 'leave_days', 
                 'overtime_hours', 'base_salary', 'allowance', 'seniority_allowance',
                 'income_tax', 'social_insurance', 'health_insurance', 
                 'unemployment_insurance', 'bonus', 'deductions', 'advance',
                 'is_paid', 'payment_date', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')
        
        # Validate month
        if month and (month < 1 or month > 12):
            self.add_error('month', 'Month must be between 1 and 12')
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Calculate net salary if not provided
        if instance.net_salary is None:
            instance.net_salary = (
                instance.base_salary 
                + instance.allowance 
                + instance.seniority_allowance 
                + instance.bonus 
                - instance.income_tax 
                - instance.social_insurance 
                - instance.health_insurance 
                - instance.unemployment_insurance 
                - instance.deductions 
                - instance.advance
            )
        
        if commit:
            instance.save()
        return instance

class SalaryProcessForm(forms.Form):
    """Form for batch processing salaries"""
    month = forms.ChoiceField(
        choices=[(i, calendar.month_name[i]) for i in range(1, 13)]
    )
    year = forms.ChoiceField()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generate year choices (current year and previous 2 years)
        current_year = date.today().year
        self.fields['year'].choices = [(y, y) for y in range(current_year-2, current_year+2)]
        # Set default to current month/year
        self.fields['month'].initial = date.today().month
        self.fields['year'].initial = current_year