from django import forms
from django.core.exceptions import ValidationError
from .models import Department, Position, AcademicTitle, EducationLevel

class DepartmentForm(forms.ModelForm):
    """Form for creating and managing departments"""
    class Meta:
        model = Department
        fields = ['department_name', 'department_code', 'description', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean_department_code(self):
        code = self.cleaned_data.get('department_code')
        if code:
            # Check if code exists for a different department
            existing_dept = Department.objects.filter(department_code=code)
            if self.instance.pk:
                existing_dept = existing_dept.exclude(pk=self.instance.pk)
            
            if existing_dept.exists():
                raise ValidationError('This department code is already in use')
        
        return code

class PositionForm(forms.ModelForm):
    """Form for creating and managing positions"""
    class Meta:
        model = Position
        fields = ['position_name', 'position_code', 'description', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean_position_code(self):
        code = self.cleaned_data.get('position_code')
        if code:
            # Check if code exists for a different position
            existing_pos = Position.objects.filter(position_code=code)
            if self.instance.pk:
                existing_pos = existing_pos.exclude(pk=self.instance.pk)
            
            if existing_pos.exists():
                raise ValidationError('This position code is already in use')
        
        return code

class AcademicTitleForm(forms.ModelForm):
    """Form for creating and managing academic titles"""
    class Meta:
        model = AcademicTitle
        fields = ['title_name', 'title_code', 'description', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class EducationLevelForm(forms.ModelForm):
    """Form for creating and managing education levels"""
    class Meta:
        model = EducationLevel
        fields = ['education_name', 'education_code', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }