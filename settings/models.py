from django.db import models
import json

class SystemSetting(models.Model):
    SETTING_TYPE_CHOICES = (
        ('string', 'String'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
        ('text', 'Text'),
    )
    
    SETTING_GROUP_CHOICES = (
        ('general', 'General Settings'),
        ('email', 'Email Settings'),
        ('attendance', 'Attendance Settings'),
        ('leave', 'Leave Management Settings'),
        ('performance', 'Performance Settings'),
        ('security', 'Security Settings'),
        ('appearance', 'Appearance Settings'),
        ('notification', 'Notification Settings'),
        ('integration', 'Integration Settings'),
    )
    
    setting_id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    value_type = models.CharField(max_length=10, choices=SETTING_TYPE_CHOICES)
    group = models.CharField(max_length=20, choices=SETTING_GROUP_CHOICES, default='general')
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    is_public = models.BooleanField(default=False, help_text='Public settings are visible to all users')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.key})"
    
    def get_typed_value(self):
        """Get the value converted to its proper type"""
        if self.value_type == 'string':
            return self.value
        elif self.value_type == 'integer':
            try:
                return int(self.value)
            except (ValueError, TypeError):
                return 0
        elif self.value_type == 'boolean':
            return self.value.lower() in ('true', 'yes', '1', 't', 'y')
        elif self.value_type == 'json':
            try:
                return json.loads(self.value)
            except json.JSONDecodeError:
                return {}
        else:  # text or other
            return self.value

class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('view', 'View'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('other', 'Other'),
    )
    
    log_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField()
    ip_address = models.CharField(max_length=50, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.action} on {self.entity_type} by {self.user}"
    
    class Meta:
        ordering = ['-timestamp']