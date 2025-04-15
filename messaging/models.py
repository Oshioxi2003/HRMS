from django.db import models
from django.template import Template, Context
from django.core.mail import send_mail
from django.conf import settings



class EmailTemplate(models.Model):
    TEMPLATE_CATEGORIES = (
        ('user', 'User Account'),
        ('leave', 'Leave Management'),
        ('attendance', 'Attendance'),
        ('performance', 'Performance'),
        ('payroll', 'Payroll & Salary'),
        ('task', 'Task Management'),
        ('workflow', 'Workflow'),
        ('system', 'System Notifications'),
    )
    
    template_id = models.AutoField(primary_key=True)
    template_code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=200)
    body_html = models.TextField()
    body_text = models.TextField()
    category = models.CharField(max_length=20, choices=TEMPLATE_CATEGORIES)
    is_active = models.BooleanField(default=True)
    variables = models.TextField(help_text='Variables to use in template, comma separated', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.template_code})"
    
    def render(self, context_dict):
        """Render template with given context"""
        context = Context(context_dict)
        subject_template = Template(self.subject)
        rendered_subject = subject_template.render(context)
        
        html_template = Template(self.body_html)
        rendered_html = html_template.render(context)
        
        text_template = Template(self.body_text)
        rendered_text = text_template.render(context)
        
        return {
            'subject': rendered_subject,
            'body_html': rendered_html,
            'body_text': rendered_text
        }
    
    def send_email(self, to_email, context_dict, from_email=None):
        """Send email using this template"""
        if not from_email:
            from_email = settings.DEFAULT_FROM_EMAIL
        
        rendered = self.render(context_dict)
        
        return send_mail(
            subject=rendered['subject'],
            message=rendered['body_text'],
            from_email=from_email,
            recipient_list=[to_email] if isinstance(to_email, str) else to_email,
            html_message=rendered['body_html'],
            fail_silently=False,
        )

class EmailLog(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    )
    
    log_id = models.AutoField(primary_key=True)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True)
    template_code = models.CharField(max_length=100)
    from_email = models.EmailField()
    to_email = models.TextField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    context_data = models.TextField(null=True, blank=True)  # JSON string of context data
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(null=True, blank=True)
    sent_date = models.DateTimeField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Email to {self.to_email} ({self.status})"
    


