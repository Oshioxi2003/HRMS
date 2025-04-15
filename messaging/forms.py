from django import forms
from .models import EmailTemplate

class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ['name', 'template_code', 'subject', 'body_html', 'body_text', 'category', 'variables', 'is_active']
        widgets = {
            'body_html': forms.Textarea(attrs={'rows': 15, 'class': 'html-editor'}),
            'body_text': forms.Textarea(attrs={'rows': 10}),
            'variables': forms.TextInput(attrs={'placeholder': 'e.g. name, email, link, date'})
        }
    
    def clean_template_code(self):
        template_code = self.cleaned_data.get('template_code')
        if ' ' in template_code:
            raise forms.ValidationError("Template code cannot contain spaces.")
        
        # Check uniqueness only on create
        if not self.instance.pk and EmailTemplate.objects.filter(template_code=template_code).exists():
            raise forms.ValidationError("Template code must be unique.")
        
        return template_code

class TestEmailForm(forms.Form):
    to_email = forms.EmailField(label="Recipient Email")

class CustomEmailForm(forms.Form):
    to_email = forms.CharField(
        label="Recipient Email(s)", 
        help_text="Separate multiple emails with commas"
    )
    subject = forms.CharField(max_length=200)
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10}),
        help_text="Plain text version of the message"
    )
    html_message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 15, 'class': 'html-editor'}),
        help_text="HTML version of the message (optional)",
        required=False
    )
    
    def clean_to_email(self):
        to_email = self.cleaned_data.get('to_email')
        emails = [email.strip() for email in to_email.split(',')]
        
        for email in emails:
            if not email:
                continue
            
            # Basic email validation
            if '@' not in email or '.' not in email:
                raise forms.ValidationError(f"Invalid email address: {email}")
        
        return emails
