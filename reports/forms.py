from django import forms
from django.core.exceptions import ValidationError
from employee.models import Department, Position
import calendar
from datetime import date, datetime

class DateRangeForm(forms.Form):
    """Base form for date range selection"""
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            self.add_error('end_date', 'End date must be after start date')
        
        return cleaned_data

class EmployeeReportForm(DateRangeForm):
    """Form for generating employee reports"""
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(status=1),
        required=False,
        help_text='Leave blank for all departments'
    )
    position = forms.ModelChoiceField(
        queryset=Position.objects.filter(status=1),
        required=False,
        help_text='Leave blank for all positions'
    )
    status = forms.ChoiceField(
        choices=[
            ('', 'All Statuses'),
            ('Working', 'Working'),
            ('Resigned', 'Resigned'),
            ('On Leave', 'On Leave')
        ],
        required=False
    )
    report_type = forms.ChoiceField(
        choices=[
            ('summary', 'Summary Report'),
            ('detailed', 'Detailed Report'),
            ('turnover', 'Turnover Report')
        ],
        initial='summary'
    )
    export_format = forms.ChoiceField(
        choices=[
            ('pdf', 'PDF'),
            ('excel', 'Excel'),
            ('csv', 'CSV')
        ],
        initial='pdf'
    )

class AttendanceReportForm(DateRangeForm):
    """Form for generating attendance reports"""
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(status=1),
        required=False,
        help_text='Leave blank for all departments'
    )
    report_type = forms.ChoiceField(
        choices=[
            ('summary', 'Summary Report'),
            ('detailed', 'Detailed Report'),
            ('absent', 'Absence Report'),
            ('overtime', 'Overtime Report')
        ],
        initial='summary'
    )
    export_format = forms.ChoiceField(
        choices=[
            ('pdf', 'PDF'),
            ('excel', 'Excel'),
            ('csv', 'CSV')
        ],
        initial='pdf'
    )

class LeaveReportForm(DateRangeForm):
    """Form for generating leave reports"""
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(status=1),
        required=False,
        help_text='Leave blank for all departments'
    )
    leave_type = forms.ChoiceField(
        choices=[
            ('', 'All Types'),
            ('Annual Leave', 'Annual Leave'),
            ('Sick Leave', 'Sick Leave'),
            ('Maternity Leave', 'Maternity Leave'),
            ('Personal Leave', 'Personal Leave'),
            ('Other', 'Other')
        ],
        required=False
    )
    status = forms.ChoiceField(
        choices=[
            ('', 'All Statuses'),
            ('Pending', 'Pending'),
            ('Approved', 'Approved'),
            ('Rejected', 'Rejected'),
            ('Cancelled', 'Cancelled')
        ],
        required=False
    )
    export_format = forms.ChoiceField(
        choices=[
            ('pdf', 'PDF'),
            ('excel', 'Excel'),
            ('csv', 'CSV')
        ],
        initial='pdf'
    )

class PayrollReportForm(forms.Form):
    """Form for generating payroll reports"""
    MONTH_CHOICES = [(i, calendar.month_name[i]) for i in range(1, 13)]
    
    month = forms.ChoiceField(choices=MONTH_CHOICES)
    year = forms.IntegerField(min_value=2000, max_value=2100)
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(status=1),
        required=False,
        help_text='Leave blank for all departments'
    )
    report_type = forms.ChoiceField(
        choices=[
            ('summary', 'Summary Report'),
            ('detailed', 'Detailed Report'),
            ('bank_transfer', 'Bank Transfer List'),
            ('tax', 'Tax Report')
        ],
        initial='summary'
    )
    export_format = forms.ChoiceField(
        choices=[
            ('pdf', 'PDF'),
            ('excel', 'Excel'),
            ('csv', 'CSV')
        ],
        initial='pdf'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default to current month/year
        today = date.today()
        self.fields['month'].initial = today.month
        self.fields['year'].initial = today.year