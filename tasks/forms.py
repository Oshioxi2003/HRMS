# tasks/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Task, TaskCategory, TaskComment
from employee.models import Employee
from django.contrib.auth import get_user_model

User = get_user_model()

class TaskForm(forms.ModelForm):
    """Form for creating and editing tasks"""
    class Meta:
        model = Task
        fields = ['title', 'description', 'category', 'assignee', 'priority', 
                 'status', 'start_date', 'due_date', 'is_recurring', 
                 'recurrence_pattern', 'attachments']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'recurrence_pattern': forms.TextInput(attrs={'placeholder': 'e.g., daily, weekly, monthly'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active categories
        self.fields['category'].queryset = TaskCategory.objects.filter(is_active=True)
        # Only show active employees
        self.fields['assignee'].queryset = Employee.objects.filter(status='Working')
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        due_date = cleaned_data.get('due_date')
        is_recurring = cleaned_data.get('is_recurring')
        recurrence_pattern = cleaned_data.get('recurrence_pattern')
        
        if start_date and due_date and start_date > due_date:
            raise ValidationError("Due date must be after start date.")
        
        if is_recurring and not recurrence_pattern:
            raise ValidationError("Recurrence pattern is required for recurring tasks.")
        
        return cleaned_data

class TaskStatusUpdateForm(forms.ModelForm):
    """Form for updating task status and progress"""
    class Meta:
        model = Task
        fields = ['status', 'progress']
        widgets = {
            'progress': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': 5})
        }
    
    def clean_progress(self):
        progress = self.cleaned_data.get('progress')
        if progress < 0 or progress > 100:
            raise ValidationError("Progress must be between 0 and 100.")
        return progress
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        progress = cleaned_data.get('progress')
        
        if status == 'Completed' and progress < 100:
            # Auto-set progress to 100% when completed
            cleaned_data['progress'] = 100
        
        if status == 'Not Started' and progress > 0:
            # Auto-set progress to 0% when not started
            cleaned_data['progress'] = 0
        
        return cleaned_data

class TaskCommentForm(forms.ModelForm):
    """Form for adding comments to tasks"""
    class Meta:
        model = TaskComment
        fields = ['comment', 'attachment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter your comment here...'})
        }

class TaskFilterForm(forms.Form):
    """Form for filtering tasks"""
    STATUS_CHOICES = (
        ('', 'All Statuses'),
    ) + Task.STATUS_CHOICES
    
    PRIORITY_CHOICES = (
        ('', 'All Priorities'),
    ) + Task.PRIORITY_CHOICES
    
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    priority = forms.ChoiceField(choices=PRIORITY_CHOICES, required=False)
    category = forms.ModelChoiceField(
        queryset=TaskCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories"
    )
    assignee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(status='Working'),
        required=False,
        empty_label="All Assignees"
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    search = forms.CharField(required=False, max_length=100)

class TaskCategoryForm(forms.ModelForm):
    """Form for task categories"""
    class Meta:
        model = TaskCategory
        fields = ['name', 'description', 'color', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'color': forms.TextInput(attrs={'type': 'color'})
        }
