from django import forms
from .models import SystemSetting

class SystemSettingForm(forms.ModelForm):
    """Form for creating and updating system settings"""
    
    class Meta:
        model = SystemSetting
        fields = ['key', 'name', 'value', 'value_type', 'group', 'description', 'is_public']
        widgets = {
            'key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., company_name, email_host'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Display name for this setting'}),
            'value': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Explain what this setting is for'}),
        }
    
    def clean_key(self):
        """Validate that key contains only letters, numbers, and underscores"""
        key = self.cleaned_data.get('key')
        if not all(c.isalnum() or c == '_' for c in key):
            raise forms.ValidationError("Key can only contain letters, numbers, and underscores.")
        return key
    
    def clean(self):
        """Additional validation based on value_type"""
        cleaned_data = super().clean()
        value_type = cleaned_data.get('value_type')
        value = cleaned_data.get('value')
        
        if not value:
            return cleaned_data
            
        # Validate integer
        if value_type == 'integer':
            try:
                int(value)
            except (ValueError, TypeError):
                self.add_error('value', "Value must be an integer for integer type.")
        
        # Validate boolean
        elif value_type == 'boolean':
            if value.lower() not in ('true', 'false', '1', '0', 'yes', 'no'):
                self.add_error('value', "Value must be 'true', 'false', '1', '0', 'yes', or 'no' for boolean type.")
        
        # Validate JSON
        elif value_type == 'json':
            try:
                import json
                json.loads(value)
            except json.JSONDecodeError:
                self.add_error('value', "Value must be valid JSON for JSON type.")
        
        return cleaned_data
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text for value field based on selected value_type
        self.fields['value_type'].widget.attrs.update({
            'class': 'form-control', 
            'onchange': 'updateValueHelpText(this.value)'
        })
        
        # Add explanation for value types
        self.fields['value_type'].help_text = """
            <div id="value-type-help">
                <small>
                    <strong>String</strong>: Simple text value<br>
                    <strong>Integer</strong>: Numeric value without decimals<br>
                    <strong>Boolean</strong>: True/False value<br>
                    <strong>JSON</strong>: JSON formatted data<br>
                    <strong>Text</strong>: Long text content
                </small>
            </div>
        """
        
        # Make form controls look good with Bootstrap
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'