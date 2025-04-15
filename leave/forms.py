from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
from .models import LeaveRequest, LeaveBalance
from datetime import date, timedelta


class LeaveRequestForm(forms.ModelForm):
    """Form for submitting leave requests"""
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'attached_file']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'attached_file': forms.FileInput(attrs={'class': 'form-control'})
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        leave_type = cleaned_data.get('leave_type')
        
        if start_date and end_date:
            # End date must be after or equal to start date
            if end_date < start_date:
                self.add_error('end_date', _('End date must be after or equal to start date.'))
            
            # Calculate business days
            business_days = self.calculate_business_days(start_date, end_date)
            if business_days < 0.5:
                self.add_error('end_date', _('Leave period must include at least half a business day.'))
            
            # Special validations based on leave type
            if leave_type == 'Sick Leave' and business_days > 30:
                self.add_error('end_date', _('Sick leave cannot exceed 30 days. Please contact HR for extended sick leave.'))
            
            # Example: Validate if future date required for certain leave types
            today = date.today()
            if leave_type in ['Annual Leave', 'Personal Leave'] and (start_date - today).days < 3:
                self.add_error('start_date', _('Annual and personal leave must be requested at least 3 days in advance.'))
        
        return cleaned_data
    
    @staticmethod
    def calculate_business_days(start_date, end_date):
        """Calculate number of business days between two dates"""
        days = 0
        current_date = start_date
        while current_date <= end_date:
            # Monday = 0, Sunday = 6
            if current_date.weekday() < 5:  
                days += 1
            current_date += timedelta(days=1)
        return days

class LeaveApprovalForm(forms.ModelForm):
    """Form for approving/rejecting leave requests"""
    class Meta:
        model = LeaveRequest
        fields = ['status', 'approval_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'approval_notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def clean_status(self):
        status = self.cleaned_data.get('status')
        if status not in ['Approved', 'Rejected']:
            raise ValidationError(_('Status must be either Approved or Rejected.'))
        return status

class LeaveBalanceForm(forms.ModelForm):
    """Form for adding/editing leave balances"""
    class Meta:
        model = LeaveBalance
        fields = ['leave_type', 'total_days', 'used_days', 'carry_over']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'total_days': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'used_days': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'carry_over': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
        }

class DateRangeForm(forms.Form):
    """Form for date range filtering"""
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))