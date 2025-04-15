from django import forms
from django.contrib.auth import get_user_model
from .models import WorkflowDefinition, WorkflowStep

User = get_user_model()

class WorkflowDefinitionForm(forms.ModelForm):
    class Meta:
        model = WorkflowDefinition
        fields = ['name', 'description', 'entity_type', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class WorkflowStepForm(forms.ModelForm):
    class Meta:
        model = WorkflowStep
        fields = ['step_name', 'description', 'step_type', 'approver_type', 
                  'specific_approver', 'is_required', 'skip_condition', 'order']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'skip_condition': forms.Textarea(attrs={'rows': 2, 
                                                  'placeholder': 'Optional: Add conditions for when this step should be skipped'}),
        }
    
    def __init__(self, *args, **kwargs):
        workflow = kwargs.pop('workflow', None)
        super().__init__(*args, **kwargs)
        
        # Only show active users for specific approver
        self.fields['specific_approver'].queryset = User.objects.filter(is_active=True)
        
        # Make approver_type required only for approval steps
        self.fields['approver_type'].required = False
        
        # Set the initial order to next available number if this is a new step
        if workflow and not self.instance.pk:
            next_order = WorkflowStep.objects.filter(workflow=workflow).count() + 1
            self.fields['order'].initial = next_order
    
    def clean(self):
        cleaned_data = super().clean()
        step_type = cleaned_data.get('step_type')
        approver_type = cleaned_data.get('approver_type')
        specific_approver = cleaned_data.get('specific_approver')
        
        # Validate approver type is set for approval steps
        if step_type == 'approval' and not approver_type:
            self.add_error('approver_type', 'Approver type is required for approval steps')
        
        # Validate specific approver is set when approver_type is specific_user
        if approver_type == 'specific_user' and not specific_approver:
            self.add_error('specific_approver', 'Specific approver is required when approver type is Specific User')
        
        return cleaned_data

class StepReorderForm(forms.Form):
    step_order = forms.CharField(widget=forms.HiddenInput())

class WorkflowStepActionForm(forms.Form):
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add comments about your decision...'}),
        required=False
    )
    
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject')
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(),
        initial='approve'
    )