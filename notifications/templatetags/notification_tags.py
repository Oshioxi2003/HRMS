from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def notification_icon(notification_type):
    """Return appropriate icon class based on notification type"""
    icons = {
        'System': 'fa-bell',
        'Leave': 'fa-calendar-alt',
        'Attendance': 'fa-clock',
        'Performance': 'fa-chart-line',
        'Contract': 'fa-file-contract',
        'Training': 'fa-graduation-cap',
        'Salary': 'fa-money-bill-wave',
        'Birthday': 'fa-birthday-cake',
        'Task': 'fa-tasks',
        'Document': 'fa-file-alt',
        'Expense': 'fa-receipt',
        'Asset': 'fa-laptop',
        'Workflow': 'fa-project-diagram',
    }
    
    return icons.get(notification_type, 'fa-bell')

@register.filter
def get_dict_item(dictionary, key):
    """Get an item from a dictionary"""
    if dictionary and key in dictionary:
        return dictionary[key]
    return False
