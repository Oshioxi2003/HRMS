from django import forms
from employee.models import Department, Position

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['department_name', 'department_code', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean_department_code(self):
        code = self.cleaned_data.get('department_code')
        if Department.objects.filter(department_code=code).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This department code is already in use.")
        return code

class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['position_name', 'position_code', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean_position_code(self):
        code = self.cleaned_data.get('position_code')
        if Position.objects.filter(position_code=code).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This position code is already in use.")
        return code