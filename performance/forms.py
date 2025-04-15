from django import forms
from django.core.exceptions import ValidationError
from .models import KPI, EmployeeEvaluation, RewardsAndDisciplinary
from employee.models import Employee, Department
import calendar
from datetime import date

class KPIForm(forms.ModelForm):
    """Form for creating and managing KPIs"""
    class Meta:
        model = KPI
        fields = ['kpi_name', 'description', 'unit', 'min_target', 'max_target',
                  'weight_factor', 'kpi_type']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        min_target = cleaned_data.get('min_target')
        max_target = cleaned_data.get('max_target')
        
        if min_target is not None and max_target is not None:
            if max_target < min_target:
                self.add_error('max_target', 'Maximum target must be greater than minimum target')
        
        return cleaned_data

class EmployeeEvaluationForm(forms.ModelForm):
    """Form for evaluating employee performance"""
    class Meta:
        model = EmployeeEvaluation
        fields = ['kpi', 'month', 'year', 'result', 'target', 'feedback']
        widgets = {
            'feedback': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set month choices
        self.fields['month'] = forms.ChoiceField(
            choices=[(i, calendar.month_name[i]) for i in range(1, 13)]
        )
        # Set default month/year
        today = date.today()
        self.fields['month'].initial = today.month
        self.fields['year'].initial = today.year
    
    def clean(self):
        cleaned_data = super().clean()
        result = cleaned_data.get('result')
        target = cleaned_data.get('target')
        kpi = cleaned_data.get('kpi')
        
        if kpi and target is not None:
            # Validate target against KPI min/max
            if kpi.min_target is not None and target < kpi.min_target:
                self.add_error('target', f'Target should be at least {kpi.min_target}')
            if kpi.max_target is not None and target > kpi.max_target:
                self.add_error('target', f'Target should not exceed {kpi.max_target}')
        
        return cleaned_data

class RewardsAndDisciplinaryForm(forms.ModelForm):
    """Form for managing rewards and disciplinary actions"""
    class Meta:
        model = RewardsAndDisciplinary
        fields = ['employee', 'type', 'content', 'decision_date', 'decision_number',
                  'amount', 'decided_by', 'attached_file', 'notes']
        widgets = {
            'decision_date': forms.DateInput(attrs={'type': 'date'}),
            'content': forms.Textarea(attrs={'rows': 4}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        type_val = self.cleaned_data.get('type')
        
        if type_val == 'Reward' and amount <= 0:
            raise ValidationError('Reward amount must be greater than zero')
        
        return amount

class PerformanceReviewForm(forms.Form):
    """Form for initiating performance review cycles"""
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(status=1),
        required=False,
        help_text='Leave blank to review all departments'
    )
    month = forms.ChoiceField(
        choices=[(i, calendar.month_name[i]) for i in range(1, 13)]
    )
    year = forms.IntegerField(min_value=2000, max_value=2100)
    review_deadline = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Deadline for completing performance reviews'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = date.today()
        self.fields['month'].initial = today.month
        self.fields['year'].initial = today.year
        # Set default deadline to end of current month
        last_day = calendar.monthrange(today.year, today.month)[1]
        self.fields['review_deadline'].initial = date(today.year, today.month, last_day)