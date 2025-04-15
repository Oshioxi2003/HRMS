from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from .utils import generate_random_password

def set_user_defaults(backend, strategy, details, user=None, *args, **kwargs):
    if user:
        # Ensure user is active regardless of prior status
        user.is_active = True
        user.status = 'Active'
        user.save()


def associate_by_email(backend, details, user=None, *args, **kwargs):
    """
    Custom pipeline function to associate a Google OAuth account with an existing user
    based on email address.
    """
    if user:
        return {'is_new': False}
    
    email = details.get('email')
    if email:
        from .utils import get_user_from_email
        user = get_user_from_email(email)
        if user:
            return {'is_new': False, 'user': user}
    
    return None

def set_user_details(backend, strategy, details, user=None, *args, **kwargs):
    """Update user details from social auth information"""
    if not user:
        return
    
    changed = False
    
    # Cập nhật thông tin từ Google nếu chưa có
    if details.get('fullname') and not (user.first_name and user.last_name):
        full_name = details.get('fullname')
        if ' ' in full_name:
            user.first_name = full_name.split(' ')[0]
            user.last_name = ' '.join(full_name.split(' ')[1:])
        else:
            user.first_name = full_name
        changed = True
    
    if details.get('first_name') and not user.first_name:
        user.first_name = details.get('first_name')
        changed = True
    
    if details.get('last_name') and not user.last_name:
        user.last_name = details.get('last_name')
        changed = True
    
    # Lưu thay đổi nếu có
    if changed:
        user.save()

def generate_password_for_sso_user(backend, strategy, details, user=None, is_new=False, *args, **kwargs):
    """Generate and email a random password for new SSO users"""
    if not user:
        return
    
    # Only for social auth users
    if not backend.name.startswith('google'):
        return
    
    request = kwargs.get('request')
    if not request:
        return
    
    # Generate random password for new users or users without usable password
    if is_new or not user.has_usable_password():
        # Generate random password
        random_password = generate_random_password(12)
        
        # Set the password
        user.set_password(random_password)
        user.save()
        
        # Send email with the password
        current_site = get_current_site(request)
        mail_subject = 'Your HRMS Account Password'
        message = render_to_string('accounts/email/sso_password_email.html', {
            'user': user,
            'domain': current_site.domain,
            'password': random_password,
            'protocol': 'https' if request.is_secure() else 'http'
        })
        
        email = EmailMessage(
            mail_subject, message, to=[user.email]
        )
        email.content_subtype = 'html'  # Send as HTML email
        email.send()