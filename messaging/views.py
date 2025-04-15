from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
import json

from .models import *
from .services import EmailService
from .forms import *
from accounts.decorators import admin_required, hr_required


@login_required
@hr_required
def email_template_list(request):
    """List all email templates"""
    category_filter = request.GET.get('category', '')
    query = request.GET.get('q', '')
    
    templates = EmailTemplate.objects.all()
    
    if category_filter:
        templates = templates.filter(category=category_filter)
    
    if query:
        templates = templates.filter(name__icontains=query) | templates.filter(template_code__icontains=query)
    
    templates = templates.order_by('-is_active', 'name')
    
    paginator = Paginator(templates, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'messaging/email_template_list.html', {
        'page_obj': page_obj,
        'category_filter': category_filter,
        'query': query,
        'categories': dict(EmailTemplate.TEMPLATE_CATEGORIES)
    })

@login_required
@admin_required
def email_template_create(request):
    """Create a new email template"""
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST)
        if form.is_valid():
            template = form.save()
            messages.success(request, "Email template created successfully.")
            return redirect('email_template_detail', template_id=template.template_id)
    else:
        form = EmailTemplateForm()
    
    return render(request, 'messaging/email_template_form.html', {
        'form': form,
        'is_create': True
    })

@login_required
@hr_required
def email_template_detail(request, template_id):
    """View email template details"""
    template = get_object_or_404(EmailTemplate, template_id=template_id)
    
    # Get available variables
    variables = []
    if template.variables:
        variables = [var.strip() for var in template.variables.split(',')]
    
    # Get recent logs for this template
    logs = EmailLog.objects.filter(template=template).order_by('-created_date')[:5]
    
    return render(request, 'messaging/email_template_detail.html', {
        'template': template,
        'variables': variables,
        'logs': logs
    })

@login_required
@admin_required
def email_template_edit(request, template_id):
    """Edit an email template"""
    template = get_object_or_404(EmailTemplate, template_id=template_id)
    
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, "Email template updated successfully.")
            return redirect('email_template_detail', template_id=template.template_id)
    else:
        form = EmailTemplateForm(instance=template)
    
    return render(request, 'messaging/email_template_form.html', {
        'form': form,
        'template': template,
        'is_create': False
    })

@login_required
@admin_required
def email_template_delete(request, template_id):
    """Delete an email template"""
    template = get_object_or_404(EmailTemplate, template_id=template_id)
    
    if request.method == 'POST':
        template.delete()
        messages.success(request, "Email template deleted successfully.")
        return redirect('email_template_list')
    
    return render(request, 'messaging/email_template_confirm_delete.html', {
        'template': template
    })

@login_required
@hr_required
def email_template_preview(request, template_id):
    """Preview an email template with sample data"""
    template = get_object_or_404(EmailTemplate, template_id=template_id)
    
    # Create sample context data
    sample_context = {}
    if template.variables:
        variables = [var.strip() for var in template.variables.split(',')]
        for var in variables:
            sample_context[var] = f"[Sample {var}]"
    
    # Render template with sample data
    try:
        rendered = template.render(sample_context)
        return render(request, 'messaging/email_template_preview.html', {
            'template': template,
            'rendered_subject': rendered['subject'],
            'rendered_html': rendered['body_html'],
            'rendered_text': rendered['body_text'],
            'sample_context': sample_context
        })
    except Exception as e:
        messages.error(request, f"Error previewing template: {str(e)}")
        return redirect('email_template_detail', template_id=template_id)

@login_required
@hr_required
def email_template_test(request, template_id):
    """Send a test email using this template"""
    template = get_object_or_404(EmailTemplate, template_id=template_id)
    
    if request.method == 'POST':
        form = TestEmailForm(request.POST)
        if form.is_valid():
            to_email = form.cleaned_data['to_email']
            
            # Create context data from form
            context_data = {}
            if template.variables:
                variables = [var.strip() for var in template.variables.split(',')]
                for var in variables:
                    var_value = request.POST.get(f'var_{var}', '')
                    context_data[var] = var_value
            
            # Send test email
            success, log = EmailService.send_email_by_template(
                template_code=template.template_code,
                to_email=to_email,
                context_dict=context_data
            )
            
            if success:
                messages.success(request, "Test email sent successfully.")
            else:
                messages.error(request, f"Failed to send test email: {log.error_message}")
            
            return redirect('email_template_detail', template_id=template_id)
    else:
        form = TestEmailForm()
    
    # Get available variables
    variables = []
    if template.variables:
        variables = [var.strip() for var in template.variables.split(',')]
    
    return render(request, 'messaging/email_template_test.html', {
        'form': form,
        'template': template,
        'variables': variables
    })

@login_required
@hr_required
def email_log_list(request):
    """List email logs"""
    status_filter = request.GET.get('status', '')
    template_filter = request.GET.get('template', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    logs = EmailLog.objects.all()
    
    if status_filter:
        logs = logs.filter(status=status_filter)
    
    if template_filter:
        logs = logs.filter(template_id=template_filter)
    
    if date_from:
        logs = logs.filter(created_date__gte=date_from)
    
    if date_to:
        logs = logs.filter(created_date__lte=date_to)
    
    logs = logs.order_by('-created_date')
    
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get templates for filter dropdown
    templates = EmailTemplate.objects.all().order_by('name')
    
    return render(request, 'messaging/email_log_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'template_filter': template_filter,
        'date_from': date_from,
        'date_to': date_to,
        'templates': templates
    })

@login_required
@hr_required
def email_log_detail(request, log_id):
    """View email log details"""
    log = get_object_or_404(EmailLog, log_id=log_id)
    
    # Parse context data
    context_data = None
    if log.context_data:
        try:
            context_data = json.loads(log.context_data)
        except json.JSONDecodeError:
            context_data = None
    
    return render(request, 'messaging/email_log_detail.html', {
        'log': log,
        'context_data': context_data
    })

@login_required
@hr_required
def send_custom_email(request):
    """Send a custom email without using a template"""
    if request.method == 'POST':
        form = CustomEmailForm(request.POST)
        if form.is_valid():
            to_email = form.cleaned_data['to_email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            html_message = form.cleaned_data['html_message']
            
            success, log = EmailService.send_custom_email(
                subject=subject,
                message=message,
                to_email=to_email,
                html_message=html_message
            )
            
            if success:
                messages.success(request, "Email sent successfully.")
                return redirect('email_log_detail', log_id=log.log_id)
            else:
                messages.error(request, f"Failed to send email: {log.error_message}")
    else:
        form = CustomEmailForm()
    
    return render(request, 'messaging/send_custom_email.html', {
        'form': form
    })




