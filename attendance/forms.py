from django import forms
from django.core.exceptions import ValidationError
from .models import Attendance, WorkShift, ShiftAssignment
from employee.models import Employee
from datetime import date, datetime, timedelta

class WorkShiftForm(forms.ModelForm):
    """Form for managing work shifts"""
    class Meta:
        model = WorkShift
        fields = ['shift_name', 'start_time', 'end_time', 'salary_coefficient', 
                  'description', 'status']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time:
            # Handle overnight shifts (where end_time < start_time)
            if end_time < start_time:
                # This is valid, but we could add a warning here
                pass
            elif end_time == start_time:
                self.add_error('end_time', 'End time must be different from start time')
        
        return cleaned_data

class ShiftAssignmentForm(forms.ModelForm):
    """Form for assigning shifts to employees"""
    class Meta:
        model = ShiftAssignment
        fields = ['employee', 'shift', 'assignment_date', 'effective_date', 
                  'end_date', 'notes', 'status']
        widgets = {
            'assignment_date': forms.DateInput(attrs={'type': 'date'}),
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
            existing_query = ShiftAssignment.objects.filter(
                employee=employee,
                status='Active'
            )
            
            if end_date:
                # Check for overlap
                existing_query = existing_query.filter(
                    effective_date__lte=end_date,
                    end_date__gte=effective_date
                ) | existing_query.filter(
                    effective_date__lte=end_date,
                    end_date__isnull=True
                )
            else:
                # No end date for new assignment, check for any future assignments
                existing_query = existing_query.filter(
                    end_date__gte=effective_date
                )
            
            # Exclude current instance if updating
            if self.instance.pk:
                existing_query = existing_query.exclude(pk=self.instance.pk)
            
            if existing_query.exists():
                self.add_error('effective_date', 
                    'This overlaps with another active shift assignment')
        
        return cleaned_data

class AttendanceForm(forms.ModelForm):
    """Form for managing attendance records"""
    class Meta:
        model = Attendance
        fields = ['employee', 'work_date', 'time_in', 'time_out', 'shift',
                  'actual_work_hours', 'overtime_hours', 'notes', 'status']
        widgets = {
            'work_date': forms.DateInput(attrs={'type': 'date'}),
            'time_in': forms.TimeInput(attrs={'type': 'time'}),
            'time_out': forms.TimeInput(attrs={'type': 'time'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        work_date = cleaned_data.get('work_date')
        time_in = cleaned_data.get('time_in')
        time_out = cleaned_data.get('time_out')
        status = cleaned_data.get('status')
        
        # Don't require time_in/time_out for non-present statuses
        if status != 'Present':
            return cleaned_data
        
        if time_in and time_out:
            # Create datetime objects for comparison using the work_date
            if work_date:
                time_in_dt = datetime.combine(work_date, time_in)
                time_out_dt = datetime.combine(work_date, time_out)
                
                # Handle overnight shifts
                if time_out < time_in:
                    time_out_dt = datetime.combine(work_date + timedelta(days=1), time_out)
                
                # Calculate work hours
                work_hours = (time_out_dt - time_in_dt).total_seconds() / 3600
                if work_hours < 0:
                    self.add_error('time_out', 'Check-out time must be after check-in time')
                else:
                    # Auto-set actual_work_hours if not provided
                    if not cleaned_data.get('actual_work_hours'):
                        cleaned_data['actual_work_hours'] = round(work_hours, 2)
        
        return cleaned_data

class AttendanceImportForm(forms.Form):
    """Form for importing attendance data from CSV/Excel"""
    import_file = forms.FileField(
        label='Select File',
        help_text='Upload a CSV or Excel file with attendance data'
    )
    date_format = forms.ChoiceField(
        choices=[
            ('DMY', 'DD/MM/YYYY'),
            ('MDY', 'MM/DD/YYYY'),
            ('YMD', 'YYYY-MM-DD')
        ],
        initial='YMD',
        help_text='Select the date format in your file'
    )
    skip_first_row = forms.BooleanField(
        initial=True, 
        required=False,
        help_text='Skip the first row (header row)'
    )