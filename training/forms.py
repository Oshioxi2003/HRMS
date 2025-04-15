# training/forms.py (expanded)
from django import forms
from django.core.exceptions import ValidationError
from .models import TrainingCourse, TrainingParticipation
from employee.models import Employee, Department

class TrainingCourseForm(forms.ModelForm):
    """Form for creating and managing training courses"""
    class Meta:
        model = TrainingCourse
        fields = ['course_name', 'description', 'start_date', 'end_date', 
                  'location', 'cost', 'organizer', 'supervisor', 'status',
                  'department', 'max_participants', 'prerequisites', 'materials', 'image']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'prerequisites': forms.Textarea(attrs={'rows': 3}),
            'materials': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'End date must be after start date')
        
        return cleaned_data

class TrainingParticipationForm(forms.ModelForm):
    """Form for managing employee participation in training"""
    class Meta:
        model = TrainingParticipation
        fields = ['employee', 'status', 'registration_date', 'expected_completion_date', 'notes']
        widgets = {
            'registration_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_completion_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        super().__init__(*args, **kwargs)
        
        if course:
            # Filter employees for department-specific courses
            if course.department:
                self.fields['employee'].queryset = Employee.objects.filter(
                    department=course.department,
                    status='Working'
                )
            # Default registration date to today and expected completion to course end date
            if course.end_date:
                self.initial['expected_completion_date'] = course.end_date

class TrainingEvaluationForm(forms.ModelForm):
    """Form for evaluating training completion"""
    class Meta:
        model = TrainingParticipation
        fields = ['status', 'score', 'achievement', 'certificate', 'actual_completion_date', 'notes']
        widgets = {
            'actual_completion_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean_score(self):
        score = self.cleaned_data.get('score')
        if score and (score < 0 or score > 100):
            raise ValidationError('Score must be between 0 and 100')
        return score
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        score = cleaned_data.get('score')
        actual_completion_date = cleaned_data.get('actual_completion_date')
        
        if status == 'Completed' and not actual_completion_date:
            self.add_error('actual_completion_date', 'Completion date is required when status is set to Completed')
        
        if status == 'Completed' and not score and not self.instance.score:
            self.add_error('score', 'Score is required when status is set to Completed')
        
        return cleaned_data

class TrainingRegistrationForm(forms.ModelForm):
    """Form for employees to register for training"""
    class Meta:
        model = TrainingParticipation
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 
                    'placeholder': 'Please provide any relevant information for your registration'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.course = kwargs.pop('course', None)
        self.employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.course:
            instance.course = self.course
        if self.employee:
            instance.employee = self.employee
        
        from datetime import date
        instance.registration_date = date.today()
        instance.status = 'Registered'
        
        # Set expected completion date if course has an end date
        if self.course and self.course.end_date:
            instance.expected_completion_date = self.course.end_date
        
        if commit:
            instance.save()
        return instance

class BulkTrainingImportForm(forms.Form):
    """Form for bulk importing training data"""
    file = forms.FileField(
        label='CSV File',
        help_text='Upload a CSV file with training course data.'
    )
    
    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name.endswith('.csv'):
            raise forms.ValidationError('Only CSV files are supported.')
        return file
