from django import forms
from django.core.exceptions import ValidationError
from datetime import timedelta
from .models import OnboardingTask, EmployeeOnboarding, EmployeeTaskStatus

class OnboardingTaskForm(forms.ModelForm):
    """Form for creating and editing onboarding tasks"""
    class Meta:
        model = OnboardingTask
        fields = [
            'task_name', 'description', 'task_type', 'is_required',
            'department_specific', 'department', 'position_specific',
            'position', 'duration_days', 'resources', 'responsible_role'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'resources': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter URLs or document references separated by new lines'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        department_specific = cleaned_data.get('department_specific')
        department = cleaned_data.get('department')
        position_specific = cleaned_data.get('position_specific')
        position = cleaned_data.get('position')
        
        if department_specific and not department:
            self.add_error('department', 'Department is required when task is department specific')
        if position_specific and not position:
            self.add_error('position', 'Position is required when task is position specific')
        
        duration_days = cleaned_data.get('duration_days')
        if duration_days is not None and duration_days <= 0:
            self.add_error('duration_days', 'Duration must be a positive number')
        
        return cleaned_data

class EmployeeOnboardingForm(forms.ModelForm):
    """Form for creating employee onboarding process"""
    class Meta:
        model = EmployeeOnboarding
        fields = ['start_date', 'target_completion_date', 'notes']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'target_completion_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        target_completion_date = cleaned_data.get('target_completion_date')
        
        if start_date and target_completion_date:
            if target_completion_date < start_date:
                self.add_error('target_completion_date', 'Target completion date must be after start date')
            # Recommend at least 1 week for onboarding
            min_recommended = start_date + timedelta(days=7)
            if target_completion_date < min_recommended:
                self.add_error('target_completion_date', 'We recommend at least 7 days for proper onboarding')
        
        return cleaned_data

class TaskStatusUpdateForm(forms.ModelForm):
    """Form for updating the status of an onboarding task"""
    class Meta:
        model = EmployeeTaskStatus
        fields = ['status', 'comments']
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter any comments or notes about task completion'}),
        }
    
    def clean_status(self):
        status = self.cleaned_data.get('status')
        original_status = self.instance.status if self.instance.pk else None
        
        # Only allow certain transitions
        allowed_transitions = {
            'Not Started': ['In Progress', 'Completed', 'Not Applicable'],
            'In Progress': ['Completed', 'Overdue', 'Not Applicable'],
            'Overdue': ['Completed', 'Not Applicable'],
            'Completed': ['Completed'],  # Once completed, cannot change
            'Not Applicable': ['Not Applicable'],  # Once marked N/A, cannot change
        }
        
        if original_status and status not in allowed_transitions.get(original_status, []):
            allowed = ', '.join(allowed_transitions.get(original_status, []))
            raise ValidationError(f"Cannot change status from '{original_status}' to '{status}'. Allowed: {allowed}")
        
        return status
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        comments = cleaned_data.get('comments')
        
        # Require comments for certain status changes
        if status in ['Not Applicable'] and not comments:
            self.add_error('comments', f"Comments are required when marking a task as {status}")
        
        return cleaned_data
