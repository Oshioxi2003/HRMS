from django.core.cache import cache
from django.conf import settings as django_settings
from .models import SystemSetting, AuditLog

class SettingsService:
    """Service for managing system settings"""
    
    CACHE_KEY_PREFIX = 'system_setting_'
    CACHE_TIMEOUT = 3600  # 1 hour
    
    @staticmethod
    def get_setting(key, default=None):
        """
        Get a setting value by key
        
        Args:
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Typed value of the setting
        """
        # Try to get from cache first
        cache_key = f"{SettingsService.CACHE_KEY_PREFIX}{key}"
        cached_value = cache.get(cache_key)
        
        if cached_value is not None:
            return cached_value
        
        # Get from database
        try:
            setting = SystemSetting.objects.get(key=key)
            value = setting.get_typed_value()
            
            # Cache the result
            cache.set(cache_key, value, SettingsService.CACHE_TIMEOUT)
            
            return value
        except SystemSetting.DoesNotExist:
            return default
    
    @staticmethod
    def set_setting(key, value, value_type=None, **kwargs):
        """
        Set a setting value
        
        Args:
            key: Setting key
            value: Setting value
            value_type: Type of the value (autodetected if not provided)
            **kwargs: Additional fields to set (name, description, group, is_public)
            
        Returns:
            SystemSetting instance
        """
        # Determine value type if not provided
        if value_type is None:
            if isinstance(value, bool):
                value_type = 'boolean'
                value = str(value).lower()
            elif isinstance(value, int):
                value_type = 'integer'
                value = str(value)
            elif isinstance(value, (dict, list)):
                value_type = 'json'
                import json
                value = json.dumps(value)
            elif isinstance(value, str) and len(value) > 255:
                value_type = 'text'
            else:
                value_type = 'string'
        
        # Get or create setting
        setting, created = SystemSetting.objects.update_or_create(
            key=key,
            defaults={
                'value': value,
                'value_type': value_type,
                **kwargs
            }
        )
        
        # Clear cache
        cache_key = f"{SettingsService.CACHE_KEY_PREFIX}{key}"
        cache.delete(cache_key)
        
        return setting
    
    @staticmethod
    def delete_setting(key):
        """Delete a setting by key"""
        try:
            setting = SystemSetting.objects.get(key=key)
            setting.delete()
            
            # Clear cache
            cache_key = f"{SettingsService.CACHE_KEY_PREFIX}{key}"
            cache.delete(cache_key)
            
            return True
        except SystemSetting.DoesNotExist:
            return False
    
    @staticmethod
    def get_settings_by_group(group):
        """Get all settings in a group"""
        return SystemSetting.objects.filter(group=group).order_by('name')
    
    @staticmethod
    def get_public_settings():
        """Get all public settings"""
        return SystemSetting.objects.filter(is_public=True).order_by('group', 'name')

class AuditService:
    """Service for managing audit logs"""
    
    @staticmethod
    def log_action(user, action, entity_type, entity_id=None, description=None, request=None):
        """
        Log a user action
        
        Args:
            user: User performing the action
            action: Action type (create, update, delete, etc.)
            entity_type: Type of entity being acted on
            entity_id: ID of the entity (optional)
            description: Description of the action (optional)
            request: HTTP request object (optional, for IP and user agent)
            
        Returns:
            AuditLog instance
        """
        # Get IP address and user agent if request provided
        ip_address = None
        user_agent = None
        
        if request:
            # Get IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            # Get user agent
            user_agent = request.META.get('HTTP_USER_AGENT')
        
        # Create log entry
        log = AuditLog.objects.create(
            user=user,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description or f"{action} on {entity_type}",
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return log
    
    @staticmethod
    def get_recent_logs(limit=50):
        """Get recent audit logs"""
        return AuditLog.objects.all().select_related('user').order_by('-timestamp')[:limit]
    
    @staticmethod
    def get_user_logs(user, limit=50):
        """Get recent audit logs for a specific user"""
        return AuditLog.objects.filter(user=user).order_by('-timestamp')[:limit]