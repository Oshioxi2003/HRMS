from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from employee.models import Employee

class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'Admin')
        
        return self.create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = (
        ('Admin', 'Admin'),
        ('HR', 'HR'),
        ('Manager', 'Manager'),
        ('Employee', 'Employee'),
    )
    
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Locked', 'Locked'),
        ('Pending Activation', 'Pending Activation'),
    )
    
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Employee')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending Activation')
    employee = models.OneToOneField(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    

class RolePermission(models.Model):
    """Model for storing user roles in the system"""
    role_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Permission(models.Model):
    """Model for storing module permissions for roles"""
    ACCESS_CHOICES = (
        ('None', 'None'),
        ('View', 'View'),
        ('Add', 'Add'),
        ('Edit', 'Edit'),
        ('Delete', 'Delete'),
        ('All', 'All'),
    )
    
    permission_id = models.AutoField(primary_key=True)
    role = models.ForeignKey(RolePermission, on_delete=models.CASCADE, related_name='permissions')
    module = models.CharField(max_length=50)
    access_right = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='None')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('role', 'module')
    
    def __str__(self):
        return f"{self.role.name} - {self.module} - {self.access_right}"

class SystemLog(models.Model):
    log_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=200)
    object_type = models.CharField(max_length=50, null=True, blank=True)
    object_id = models.IntegerField(null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    ip = models.CharField(max_length=50, null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user} - {self.action} ({self.timestamp})"
