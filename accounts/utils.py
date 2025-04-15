from django.contrib.auth import get_user_model
from django.conf import settings
from employee.models import Employee
import random
import string

User = get_user_model()

def get_user_from_email(email):
    """Lấy user hiện có hoặc tạo mới từ email Google"""
    try:
        # Kiểm tra nếu user đã tồn tại
        return User.objects.get(email=email)
    except User.DoesNotExist:
        # Kiểm tra nếu có nhân viên với email này nhưng chưa có tài khoản
        try:
            employee = Employee.objects.get(email=email)
            
            # Tạo username từ email
            username = email.split('@')[0]
            base_username = username
            counter = 1
            
            # Đảm bảo username duy nhất
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Tạo user mới
            user = User.objects.create(
                username=username,
                email=email,
                first_name=employee.first_name if hasattr(employee, 'first_name') else '',
                last_name=employee.last_name if hasattr(employee, 'last_name') else '',
                is_active=True,
                role='Employee',
                status='Active',
                employee=employee
            )
            
            return user
        except Employee.DoesNotExist:
            # Tạo user mới không liên kết với employee
            username = email.split('@')[0]
            base_username = username
            counter = 1
            
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User.objects.create(
                username=username,
                email=email,
                is_active=True,
                role='Employee',
                status='Active'
            )
            
            return user

def generate_random_password(length=12):
    """Generate a secure random password with specified length"""
    # Define character sets for password
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special_chars = '!@#$%^&*()-_=+[]{}|;:,.<>?'
    
    # Ensure at least one character from each set
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special_chars)
    ]
    
    # Fill remaining characters
    remaining_length = length - len(password)
    all_chars = lowercase + uppercase + digits + special_chars
    password.extend(random.choice(all_chars) for _ in range(remaining_length))
    
    # Shuffle to avoid predictable pattern
    random.shuffle(password)
    
    return ''.join(password)