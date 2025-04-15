import json
import traceback
from django.utils import timezone
from django.template import Template, Context
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from .models import EmailTemplate, EmailLog

class EmailService:
    @staticmethod
    def get_template(template_code):
        """Get email template by its code"""
        try:
            return EmailTemplate.objects.get(template_code=template_code, is_active=True)
        except EmailTemplate.DoesNotExist:
            return None
    
    @staticmethod
    def send_email_by_template(template_code, to_email, context_dict, from_email=None):
        """
        Send email using a template
        
        Args:
            template_code: Code of the email template to use
            to_email: Recipient email address(es)
            context_dict: Dictionary of variables to use in the template
            from_email: Sender email address (optional)
            
        Returns:
            Boolean indicating success and EmailLog instance
        """
        if not from_email:
            from_email = settings.DEFAULT_FROM_EMAIL
        
        # Convert to_email to list if it's a string
        recipient_list = [to_email] if isinstance(to_email, str) else to_email
        
        # Create email log entry
        email_log = EmailLog.objects.create(
            template_code=template_code,
            from_email=from_email,
            to_email=', '.join(recipient_list),
            context_data=json.dumps(context_dict),
            status='pending'
        )
        
        # Get template
        template = EmailService.get_template(template_code)
        if not template:
            email_log.status = 'failed'
            email_log.error_message = f"Template with code {template_code} not found or inactive"
            email_log.save()
            return False, email_log
        
        email_log.template = template
        
        try:
            # Render template
            rendered = template.render(context_dict)
            email_log.subject = rendered['subject']
            email_log.body = rendered['body_html']
            
            # Send email
            email = EmailMultiAlternatives(
                subject=rendered['subject'],
                body=rendered['body_text'],
                from_email=from_email,
                to=recipient_list
            )
            
            email.attach_alternative(rendered['body_html'], "text/html")
            email.send()
            
            # Update log
            email_log.status = 'sent'
            email_log.sent_date = timezone.now()
            email_log.save()
            
            return True, email_log
        
        except Exception as e:
            # Log error
            email_log.status = 'failed'
            email_log.error_message = str(e)
            email_log.save()
            
            # Print error for debugging
            print(f"Error sending email: {e}")
            traceback.print_exc()
            
            return False, email_log
    
    @staticmethod
    def send_custom_email(subject, message, to_email, from_email=None, html_message=None):
        """
        Send a custom email without using a template
        
        Args:
            subject: Email subject
            message: Plain text message
            to_email: Recipient email address(es)
            from_email: Sender email address (optional)
            html_message: HTML version of the message (optional)
            
        Returns:
            Boolean indicating success and EmailLog instance
        """
        if not from_email:
            from_email = settings.DEFAULT_FROM_EMAIL
        
        # Convert to_email to list if it's a string
        recipient_list = [to_email] if isinstance(to_email, str) else to_email
        
        # Create email log entry
        email_log = EmailLog.objects.create(
            template_code='custom_email',
            from_email=from_email,
            to_email=', '.join(recipient_list),
            subject=subject,
            body=html_message or message,
            status='pending'
        )
        
        try:
            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            
            # Update log
            email_log.status = 'sent'
            email_log.sent_date = timezone.now()
            email_log.save()
            
            return True, email_log
        
        except Exception as e:
            # Log error
            email_log.status = 'failed'
            email_log.error_message = str(e)
            email_log.save()
            
            # Print error for debugging
            print(f"Error sending email: {e}")
            traceback.print_exc()
            
            return False, email_log